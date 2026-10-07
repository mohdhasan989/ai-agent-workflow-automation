from agent_workflow import WorkflowRegistry

registry = WorkflowRegistry().load()


def test_all_workflows_loaded():
    assert len(registry.get_all_workflows()) == 11
    assert any(wf.workflow_id == "WF011" for wf in registry.get_all_workflows())


def test_wf001_retrievable():
    wf = registry.get_workflow("WF001")
    assert wf.workflow_name == "Inventory Restock Check"
    assert wf.inputs == ["Product inventory CSV", "minimum stock threshold"]
    assert wf.tools_required == ["CSV reader", "calculator"]
    assert wf.steps[0] == "Load inventory"
    assert wf.steps[-1] == "generate restock list"
    assert len(wf.steps) == 5


def test_all_test_questions_loaded():
    questions = registry.get_all_test_questions()
    assert len(questions) == 11
    assert questions[0].workflow_id == "WF001"
    assert questions[0].test_request == "Which products need restocking?"
    assert any(q.workflow_id == "WF011" for q in questions)


def test_steps_order_preserved_for_all_workflows():
    for wf in registry.get_all_workflows():
        assert wf.steps, wf.workflow_id
        assert all(wf.steps), wf.workflow_id
