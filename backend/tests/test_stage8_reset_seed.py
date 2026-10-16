from app.core.database import Base, SessionLocal, engine
from app.models import Candidate
from scripts.reset_seed import main as reset_seed


def test_stage8_reset_seed_script() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    reset_seed()

    with SessionLocal() as db:
        assert db.get(Candidate, "cand_lin_chen") is not None
