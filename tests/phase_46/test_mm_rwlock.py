"""Phase 46 — MM reader-writer lock, writer-preferred (ADR-0164)."""

from __future__ import annotations

import threading
import time

from mindsos_intelligence.rwlock import RWLock


def test_concurrent_readers_do_not_block():
    lock = RWLock()
    lock.acquire_read()
    lock.acquire_read()
    lock.release_read()
    lock.release_read()


def test_write_excludes_while_reader_holds():
    lock = RWLock()
    lock.acquire_read()
    acquired = threading.Event()

    def writer():
        lock.acquire_write()
        acquired.set()
        lock.release_write()

    t = threading.Thread(target=writer)
    t.start()
    assert not acquired.wait(0.2)
    lock.release_read()
    assert acquired.wait(2)
    t.join()


def test_writer_preferred_blocks_new_readers():
    lock = RWLock()
    lock.acquire_read()
    writer_in = threading.Event()
    writer_done = threading.Event()

    def writer():
        lock.acquire_write()
        writer_in.set()
        lock.release_write()
        writer_done.set()

    wt = threading.Thread(target=writer)
    wt.start()
    time.sleep(0.1)

    reader2_in = threading.Event()

    def reader2():
        lock.acquire_read()
        reader2_in.set()
        lock.release_read()

    rt = threading.Thread(target=reader2)
    rt.start()
    assert not reader2_in.wait(0.2)
    assert not writer_in.is_set()
    lock.release_read()
    assert writer_done.wait(2)
    assert reader2_in.wait(2)
    wt.join()
    rt.join()


def test_context_managers():
    lock = RWLock()
    with lock.read_locked():
        pass
    with lock.write_locked():
        pass
