import pytest
from unittest.mock import MagicMock
from google.adk.tools import ToolContext
from llms_gen_agent.tools import create_file_batches
from llms_gen_agent.sub_agents.doc_summariser.tools import process_batch_selection, update_summaries, finalize_summaries

@pytest.fixture
def mock_tool_context():
    context = MagicMock(spec=ToolContext)
    context.state = {}
    context.actions = MagicMock()
    context.actions.escalate = MagicMock() # Make escalate a mock object
    return context

# --- Tests for create_file_batches ---

def test_create_file_batches_empty_list(mock_tool_context):
    mock_tool_context.state["files"] = []
    batches = create_file_batches(mock_tool_context, batch_size=10)
    assert batches == []
    assert mock_tool_context.state["batches"] == []

def test_create_file_batches_perfect_division(mock_tool_context):
    mock_tool_context.state["files"] = ["file1.txt", "file2.txt", "file3.txt", "file4.txt"]
    batches = create_file_batches(mock_tool_context, batch_size=2)
    assert batches == [["file1.txt", "file2.txt"], ["file3.txt", "file4.txt"]]
    assert mock_tool_context.state["batches"] == [["file1.txt", "file2.txt"], ["file3.txt", "file4.txt"]]

def test_create_file_batches_imperfect_division(mock_tool_context):
    mock_tool_context.state["files"] = ["file1.txt", "file2.txt", "file3.txt", "file4.txt", "file5.txt"]
    batches = create_file_batches(mock_tool_context, batch_size=2)
    assert batches == [["file1.txt", "file2.txt"], ["file3.txt", "file4.txt"], ["file5.txt"]]
    assert mock_tool_context.state["batches"] == [["file1.txt", "file2.txt"], ["file3.txt", "file4.txt"], ["file5.txt"]]

def test_create_file_batches_batch_size_one(mock_tool_context):
    mock_tool_context.state["files"] = ["file1.txt", "file2.txt"]
    batches = create_file_batches(mock_tool_context, batch_size=1)
    assert batches == [["file1.txt"], ["file2.txt"]]
    assert mock_tool_context.state["batches"] == [["file1.txt"], ["file2.txt"]]

def test_create_file_batches_batch_size_larger_than_files(mock_tool_context):
    mock_tool_context.state["files"] = ["file1.txt", "file2.txt"]
    batches = create_file_batches(mock_tool_context, batch_size=5)
    assert batches == [["file1.txt", "file2.txt"]]
    assert mock_tool_context.state["batches"] == [["file1.txt", "file2.txt"]]

# --- Tests for process_batch_selection ---

def test_process_batch_selection_first_batch(mock_tool_context):
    mock_tool_context.state["batches"] = [["f1"], ["f2"]]
    result = process_batch_selection(mock_tool_context)
    assert result["status"] == "batch_selected"
    assert mock_tool_context.state["current_batch"] == ["f1"]
    assert mock_tool_context.state["batches"] == [["f2"]]
    assert mock_tool_context.state["loop_iteration"] == 1

def test_process_batch_selection_subsequent_batch(mock_tool_context):
    mock_tool_context.state["batches"] = [["f2"]]
    mock_tool_context.state["loop_iteration"] = 1
    result = process_batch_selection(mock_tool_context)
    assert result["status"] == "batch_selected"
    assert mock_tool_context.state["current_batch"] == ["f2"]
    assert mock_tool_context.state["batches"] == []
    assert mock_tool_context.state["loop_iteration"] == 2

def test_process_batch_selection_no_more_batches(mock_tool_context):
    mock_tool_context.state["batches"] = []
    mock_tool_context.state["loop_iteration"] = 2
    result = process_batch_selection(mock_tool_context)
    assert result["status"] == "no_more_batches"
    assert mock_tool_context.actions.escalate is True
    assert mock_tool_context.state["loop_iteration"] == 2 # Should not increment if no batches

# --- Tests for update_summaries ---

def test_update_summaries_initial(mock_tool_context):
    mock_tool_context.state["batch_summaries"] = {"batch_summaries": {"f1": "s1", "f2": "s2"}}
    result = update_summaries(mock_tool_context)
    assert result["status"] == "success"
    assert mock_tool_context.state["all_summaries"] == {"f1": "s1", "f2": "s2"}

def test_update_summaries_merge(mock_tool_context):
    mock_tool_context.state["all_summaries"] = {"f1": "s1"}
    mock_tool_context.state["batch_summaries"] = {"batch_summaries": {"f2": "s2", "f3": "s3"}}
    result = update_summaries(mock_tool_context)
    assert result["status"] == "success"
    assert mock_tool_context.state["all_summaries"] == {"f1": "s1", "f2": "s2", "f3": "s3"}

def test_update_summaries_empty_batch(mock_tool_context):
    mock_tool_context.state["all_summaries"] = {"f1": "s1"}
    mock_tool_context.state["batch_summaries"] = {"batch_summaries": {}}
    result = update_summaries(mock_tool_context)
    assert result["status"] == "success"
    assert mock_tool_context.state["all_summaries"] == {"f1": "s1"}

# --- Tests for finalize_summaries ---

def test_finalize_summaries_basic(mock_tool_context):
    mock_tool_context.state["all_summaries"] = {"f1": "s1", "f2": "s2"}
    mock_tool_context.state["project_summary_raw"] = {"project_summary": "Project overview."}
    result = finalize_summaries(mock_tool_context)
    assert result["status"] == "success"
    expected_doc_summaries = {
        "summaries": {
            "f1": "s1",
            "f2": "s2",
            "project": "Project overview."
        }
    }
    assert mock_tool_context.state["doc_summaries"] == expected_doc_summaries

def test_finalize_summaries_no_project_summary(mock_tool_context):
    mock_tool_context.state["all_summaries"] = {"f1": "s1"}
    # project_summary_raw is missing or empty
    result = finalize_summaries(mock_tool_context)
    assert result["status"] == "success"
    expected_doc_summaries = {
        "summaries": {
            "f1": "s1",
            "project": "No project summary found."
        }
    }
    assert mock_tool_context.state["doc_summaries"] == expected_doc_summaries

def test_finalize_summaries_empty_all_summaries(mock_tool_context):
    mock_tool_context.state["all_summaries"] = {}
    mock_tool_context.state["project_summary_raw"] = {"project_summary": "Project overview."}
    result = finalize_summaries(mock_tool_context)
    assert result["status"] == "success"
    expected_doc_summaries = {
        "summaries": {
            "project": "Project overview."
        }
    }
    assert mock_tool_context.state["doc_summaries"] == expected_doc_summaries
