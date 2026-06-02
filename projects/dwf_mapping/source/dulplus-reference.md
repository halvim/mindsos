# DULplus Class Reference (condensed)

## Perdurants (things that unfold in time)
- `dul:Action` — an intentional event performed by an agent (e.g., running a meeting)
- `dul:Event` — any perdurant (non-stative, may or may not be agentive) — often used when neither Action nor State applies cleanly (e.g., an earthquake, a flash)
- `dul:State` — a stative perdurant that holds of an entity homogeneously (e.g., being dizzy, existing)
- `dul:Process` — a non-homeomeric stative perdurant involving gradual change (e.g., aging, erosion)
- `dul:Achievement` — an instantaneous telic event (reaching an endpoint, e.g., arriving)
- `dul:CognitiveEvent` — a cognitive/mental event (e.g., realizing, learning)
- `dul:CognitiveState` — a cognitive/mental state (e.g., believing, knowing, understanding)
- `dul:EventType` — a type/kind of event (abstracting from instances)
- `dul:Task` — a description of work to be done
- `dul:Situation` — a complex state of affairs involving multiple entities

## Qualities & Regions (attributes and their value spaces)
- `dul:Quality` — an attribute or property of an entity (e.g., the redness of this rose)
- `dul:PhysicalAttribute` — a measurable physical quality (e.g., size, color, temperature, weight)
- `dul:Region` — a value/position in a quality space (quale)
- `dul:TimeInterval` — temporal region (a time period)
- `dul:SpaceRegion` — spatial region
- `dul:Place` — a place/location
- `dul:PhysicalPlace` — a physical location

## Physical Endurants (tangible persisting things)
- `dul:PhysicalObject` — a tangible persisting object
- `dul:DesignedArtifact` — an object made for a purpose (tools, vehicles, clothing)
- `dul:Organism` — a living entity (plants, animals)
- `dul:BiologicalObject` — a biological entity (body parts, organs, cells)
- `dul:PhysicalBody` — a body
- `dul:Person` — a human
- `dul:PhysicalAgent` — a physical agent
- `dul:Personification` — a personification

## Amounts of Matter (stuff)
- `dul:Amount` — a quantity of something
- `dul:Substance` — a kind of matter
- `dul:FunctionalSubstance` — a substance with a specific function (fuel, medicine)
- `dul:ChemicalObject` — a chemical compound

## Non-Physical Endurants (abstract or informational)
- `dul:InformationObject` — an abstract information-bearing thing
- `dul:InformationRealization` — a physical realization of information (text, speech)
- `dul:Narrative` — a story/narrative
- `dul:SocialRelation` — a social relationship

## Descriptions (formalized conceptual structures)
- `dul:Description` — a structured description
- `dul:Plan` — a plan for achieving goals
- `dul:Goal` — an aim
- `dul:Method` — a method
- `dul:Theory` — a theory
- `dul:Norm` — a norm or rule
- `dul:Obligation` — an obligation
- `dul:Right` — a right

## Concepts & Roles
- `dul:Concept` — a general category/type
- `dul:Role` — a role an entity plays
- `dul:Parameter` — a parameter
- `dul:Pattern` — a pattern
- `ontopic:Topic` — a topic of discourse
- `rol:Status` — a status

## Collections & Groups
- `dul:Collection` — a group/collection
- `dul:Collective` — an organized collective
- `dul:Organization` — a structured group of agents
- `coll:Taxon` — a taxonomic group (genus, species)
- `coll:AgentCollection` — a collection of agents
- `coll:GeneticCollection` — a genetic collection
- `coll:InformationCollection` — a collection of information

## Abstract
- `dul:Abstract` — an abstract entity
- `dul:Set` — a set
- `owl:Thing` — most general (use only as fallback)

## Key distinctions
- **Action vs State**: Action is agentive doing; State is static being.
- **Event vs Achievement**: Event is general occurrence; Achievement is telic endpoint-reaching.
- **Process vs State**: Process involves change over time; State holds homogeneously.
- **Quality vs Region**: Quality is the attribute (redness); Region is the value (a particular shade of red).
- **Organism vs BiologicalObject**: Organism = whole living entity; BiologicalObject = part (organ, cell).
- **Substance vs FunctionalSubstance**: Substance is matter type; FunctionalSubstance emphasizes function.
- **PhysicalObject vs DesignedArtifact**: DesignedArtifact implies human-made with purpose.
- **Person vs Role**: Person is rigid (once a person, always a person); Role is anti-rigid (can gain/lose).
- **InformationObject vs InformationRealization**: Object is abstract content; Realization is physical form (spoken/written).
