import pytest
import shutil
from pipelines import CodeMemoryPipeline

@pytest.fixture(scope="session")
def memory_pipeline_new():
    """Create a brand new memory pipeline."""

    # clear previous persisted data
    try:
        shutil.rmtree("./.test_temp")
    except FileNotFoundError:
        # eat file not found exception,
        # if it doesn't exist, we are happy
        pass

    memory = CodeMemoryPipeline(persist_directory="./.test_temp")

    memory.ingest("test_data/test_repo")
    yield memory

def test_code_memory_init_new(memory_pipeline_new):
    """Test if we could successfully initialize a brand new memory pipeline.
    
    This also depends on ingest() functioning properly, but we more or less
    have to test that in the fixture, rather than the test itself.
    """
    assert memory_pipeline_new.has_vector_db()
    assert memory_pipeline_new.ready_for_retrieval()

def test_code_memory_invoke_new(memory_pipeline_new):
    """Test querying the memory pipeline with ``invoke``"""
    documents = memory_pipeline_new.invoke("Tell me about the README")

    assert len(documents) > 0

    # the best match should be the readme itself.
    # the word "readme" appears several times in the readme,
    # we will check if the best match contains the word "readme".
    assert "readme" in documents[0].page_content

def test_code_memory_invoke_new_extension(memory_pipeline_new):
    """Test querying the memory pipeline with ``invoke`` about
    a text file.
    """
    documents = memory_pipeline_new.invoke("What file has .txt extension?")

    assert len(documents) > 0

    # the best match should be the .txt file in the subdirectory,
    # which contains the word "subdirectory"
    assert "subdirectory" in documents[0].page_content