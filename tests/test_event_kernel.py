from photonstrust.events.kernel import Event, EventKernel


def test_event_ordering():
    kernel = EventKernel()
    kernel.schedule(Event(time_ns=5.0, priority=1, event_type="a", node_id="n1"))
    kernel.schedule(Event(time_ns=1.0, priority=1, event_type="b", node_id="n2"))
    kernel.schedule(Event(time_ns=1.0, priority=0, event_type="c", node_id="n3"))

    log = kernel.run()
    assert [evt.event_type for evt in log] == ["c", "b", "a"]


def test_event_ordering_is_stable_for_equal_time_and_priority():
    kernel = EventKernel()
    kernel.schedule(Event(time_ns=1.0, priority=1, event_type="first", node_id="n1"))
    kernel.schedule(Event(time_ns=1.0, priority=1, event_type="second", node_id="n2"))
    kernel.schedule(Event(time_ns=1.0, priority=1, event_type="third", node_id="n3"))

    log = kernel.run()
    assert [evt.event_type for evt in log] == ["first", "second", "third"]


def test_run_until_preserves_future_events():
    kernel = EventKernel()
    kernel.schedule(Event(time_ns=1.0, priority=0, event_type="early", node_id="n1"))
    kernel.schedule(Event(time_ns=5.0, priority=0, event_type="late", node_id="n2"))

    log_partial = kernel.run(until_ns=2.0)
    assert [evt.event_type for evt in log_partial] == ["early"]

    log_full = kernel.run()
    assert [evt.event_type for evt in log_full] == ["early", "late"]


def test_trace_summary_mode_captures_counts_only():
    kernel = EventKernel(trace_mode="summary")
    kernel.schedule(Event(time_ns=1.0, priority=0, event_type="emission", node_id="n1"))
    kernel.schedule(Event(time_ns=2.0, priority=0, event_type="emission", node_id="n2"))
    kernel.schedule(Event(time_ns=3.0, priority=0, event_type="detection", node_id="n3"))

    kernel.run()

    summary = kernel.trace_summary()
    assert summary["event_count"] == 3
    assert summary["recorded_count"] == 0
    assert summary["counts_by_type"] == {"detection": 1, "emission": 2}


def test_trace_full_mode_produces_stable_hash():
    kernel_a = EventKernel(seed=7, trace_mode="full")
    kernel_b = EventKernel(seed=7, trace_mode="full")

    for kernel in (kernel_a, kernel_b):
        kernel.schedule(
            Event(
                time_ns=1.0,
                priority=0,
                event_type="emission",
                node_id="node_a",
                parent_event_ids=["seed"],
                payload={"round": 1, "noise": "low"},
            )
        )
        kernel.schedule(
            Event(
                time_ns=1.0,
                priority=1,
                event_type="detection",
                node_id="node_b",
                payload={"click": True},
            )
        )
        kernel.run()

    assert kernel_a.trace_records() == kernel_b.trace_records()
    assert kernel_a.trace_hash() == kernel_b.trace_hash()


def test_trace_sampled_mode_is_seed_deterministic():
    kernel_a = EventKernel(seed=42, trace_mode="sampled", trace_sample_rate=0.5)
    kernel_b = EventKernel(seed=42, trace_mode="sampled", trace_sample_rate=0.5)

    for i in range(20):
        evt = Event(time_ns=float(i), priority=0, event_type="tick", node_id="n")
        kernel_a.schedule(evt)
    for i in range(20):
        evt = Event(time_ns=float(i), priority=0, event_type="tick", node_id="n")
        kernel_b.schedule(evt)

    kernel_a.run()
    kernel_b.run()
    assert kernel_a.trace_records() == kernel_b.trace_records()
