# The LLM credential broker contract (level 2)

**What this document is.** The wire a credential broker must speak so that
MindsOS can call a model *without ever holding the credential*. It is written
so a deployment can implement its own broker against it; `mindsos_broker` is
the reference implementation core ships, and it is an implementer of this
contract rather than a definition of it.

⚠ **Level 2 is a wrapper around the adapter, not a resolver.** The credential
never reaches MindsOS, so there is nothing for MindsOS to resolve. This is
stated in `mindsos_llm/credentials.py` and it is the seam the design turns on:
modelling level 2 as "a resolver that returns nothing" would be a lie with a
return type.

## The shape

A broker is an HTTP endpoint that accepts **one POST** and does three things:

1. checks that the request speaks this contract,
2. adds the vendor credential,
3. forwards the body **unchanged** to the vendor and returns what came back.

It is a **transparent proxy of the vendor's own request**. MindsOS composes the
exact body the vendor expects — the model, the forced tool, the schema, the
prompt — and the broker changes exactly two things about it: where it goes, and
the credential it did not carry.

**Why not a MindsOS-native protocol** (in which the broker composes the vendor
call itself): every rule in `mindsos_llm/seam.py` — no repair layer, no
free-text fallback, unasked keys refused rather than stripped, no silent retry
— would then have to be re-asserted inside somebody else's program, where core
cannot guard it.

## The request

| | |
|---|---|
| Method | `POST` |
| Endpoint | `https://` anywhere, or `http://` on a loopback **literal** (`127.0.0.1`, `::1`) |
| `x-mindsos-broker-protocol` | `1` — the version of this contract |
| `x-mindsos-broker-vendor` | the vendor id whose wire this body speaks, e.g. `anthropic` |
| Other headers | the vendor's own (`content-type`, the vendor's API-version header, …) |
| Body | the vendor's request body, byte for byte |
| Credential | **absent** |

⚠ **The endpoint rule is deliberately not the one `require_https` applies to a
credentialled call.** That rule exists because *"this request carries a
credential"*. A brokered request carries none — but it does carry the
customer's source text, so plaintext is refused anywhere it could leave the
machine and permitted on the loopback literals, where it cannot. `localhost` is
**not** accepted: a name is resolved, and what it resolves to is not this
contract's to promise.

## The response

| | |
|---|---|
| `x-mindsos-broker-protocol` | `1` — echoed on **every** response, refusals included |
| 2xx | the vendor's response body, unchanged |
| 400 | the request did not speak this contract (wrong or missing version; wrong or missing vendor; a body length the broker will not buffer) |
| 502 | the upstream failed. **Body empty.** |

**A missing or different echo is refused, never accommodated.**
`BrokerContractViolated` is raised and the call fails. There is no negotiation
and no fallback: a broker one version behind would otherwise do something
adjacent to what was asked, and the failure would surface as a wrong answer
rather than as a refusal. The echo is on the refusals too, so a client can tell
*"your broker refused you"* from *"something else is listening on that port"* —
different faults, fixed by different people.

**502 carries an empty body, and that is not fastidiousness.**
`mindsos_llm.seam.send` refuses a non-2xx *without reading the body* so that a
provider's error page cannot reach a reader. A broker that relayed it would
defeat that from outside, and error pages are where providers put account
identifiers.

## What a broker must not do

* **Rewrite the body.** Not the model, not the tool, not the schema, not the
  prompt. A "helpful" adjustment is a silent repair layer one process further
  out, invisible to core — which would still be composing a correct request and
  receiving a plausible answer.
* **Retry.** `no_silent_retry` is a property core asserts of a transport; a
  retry inside the broker makes the census of what was actually sent
  unknowable, which is the property that rule protects.
* **Log the body.** It holds the prompt and the customer's source text.
* **Forward this contract's own headers upstream.** They mean nothing to a
  vendor and they fingerprint the deployment.
* **Bind anything but loopback**, unless the operator means to run a
  credential-adding proxy reachable from the network — anyone who can reach it
  can spend the credential.

## What level 2 does and does not hide

**Does:** the credential. MindsOS has no parameter through which one could
arrive — `build_brokered_transport` has no `resolve_credential` and
`broker_headers` takes no credential — so it is a property of the shape rather
than of a check over it.

**Does not:** the request. The broker sees the prompt and the source text.
That is acceptable because it is the *user's own* broker; it is written here so
nobody deploys a shared one believing level 2 hides more than the key.

## The reference broker

```
MINDSOS_BROKER_CREDENTIAL_VAR=ANTHROPIC_API_KEY python -m mindsos_broker
```

It prints the URL it bound. Configuration is environment-only — a command line
reaches shell history and a process listing, and this is the one program in the
tree meant to be near a credential. `MINDSOS_BROKER_VENDOR` (default
`anthropic`), `MINDSOS_BROKER_UPSTREAM` and
`MINDSOS_BROKER_CREDENTIAL_HEADER` (both default to the vendor adapter's own
values, read from the adapter rather than copied), `MINDSOS_BROKER_HOST`
(default `127.0.0.1`) and `MINDSOS_BROKER_PORT` (default `0`) are the rest.

⚠ `mindsos_broker` is a **separate top-level package, and `mindsos_llm` may not
import it** — pinned by `tests/llm_seam/test_import_isolation_mindsos_llm.py`.
It is the one program here that deliberately holds a credential, so that the
package which makes the model call remains structurally unable to.

## Configuring a client

```python
client = mindsos_llm.build_client(
    vendor_id="anthropic",
    mode="live",
    credential_level=2,          # required: there is no resolver to read it from
    broker_url="http://127.0.0.1:8787",
    model_id=..., model_version=...,
    resolve_prompt=..., tool_name=..., tool_description=...,
)
```

⚠ **`mindsos_server` cannot store a level-2 configuration today**, and that is
a deferral rather than an oversight (`core-llm-level-2-l0-custody`). L0 stores
a credential **kind**, every kind declares the levels its SOURCE can produce,
and at level 2 there is no credential for a source to produce — a broker is a
wrapper around an adapter, not a kind. So level 2 is configured by the
deployment at client construction until a first-run picker needs to offer it.
The re-open trigger is exactly that.
