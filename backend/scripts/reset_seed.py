from app.core.database import Base, SessionLocal, engine
from app.core.seed import seed_demo_data
from app.services.llm_eval import LLMEvalService
from app.services.llm_memory import LLMMemoryService


def main() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_demo_data(db)
        eval_service = LLMEvalService()
        eval_service.seed_dataset(db)
        memory_service = LLMMemoryService()
        for candidate_id in ("cand_lin_chen", "cand_maya_singh", "cand_zhou_yu"):
            memory_service.build_candidate_memory(db, candidate_id)
    print("TalentNet demo data reset complete.")


if __name__ == "__main__":
    main()
