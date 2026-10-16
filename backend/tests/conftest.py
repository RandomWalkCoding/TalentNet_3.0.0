import os
import tempfile
from uuid import uuid4
from pathlib import Path


test_db_path = Path(tempfile.gettempdir()) / f"talentnet_pytest_{uuid4().hex}.db"
os.environ["TALENTNET_DATABASE_URL"] = f"sqlite:///{test_db_path.as_posix()}"
