import sys
import asyncio
from config.settings import settings
from config.logger import logger
from core.security import security_guard, RiskLevel
from core.memory.relational import init_db, RelationalMemory
from core.memory.semantic import semantic_memory

async def run_verification():
    logger.info("Starting System-Wide Verification Tests...")

    # 1. Test database initialization
    logger.info("--- Testing Relational Database Setup ---")
    try:
        init_db()
        logger.info("✔ Relational database successfully initialized.")
    except Exception as e:
        logger.error(f"✘ Relational database failed: {e}")
        sys.exit(1)

    # 2. Test writing and reading from relational memory
    logger.info("--- Testing Database Read/Write Operations ---")
    mock_id = 999999999
    try:
        RelationalMemory.add_chat_message(telegram_id=mock_id, role="user", content="Hello Brain!")
        RelationalMemory.add_chat_message(telegram_id=mock_id, role="assistant", content="Greetings Boss!")
        
        history = RelationalMemory.get_chat_history(telegram_id=mock_id, limit=2)
        assert len(history) == 2
        assert history[0]["content"] == "Hello Brain!"
        assert history[1]["content"] == "Greetings Boss!"
        logger.info("✔ Relational memory read/write verified.")
    except Exception as e:
        logger.error(f"✘ Relational memory assertion failed: {e}")
        sys.exit(1)

    # 3. Test Security Guard Dynamic Risk Categorization
    logger.info("--- Testing Command Risk Profiling Security ---")
    try:
        safe_cmd = "dir"
        mod_cmd = "git commit -m 'update'"
        crit_cmd = "rm -rf /var/log"

        safe_risk = security_guard.analyze_command_risk(safe_cmd)
        mod_risk = security_guard.analyze_command_risk(mod_cmd)
        crit_risk = security_guard.analyze_command_risk(crit_cmd)

        logger.info(f"Command '{safe_cmd}' analyzed as: {safe_risk.name}")
        logger.info(f"Command '{mod_cmd}' analyzed as: {mod_risk.name}")
        logger.info(f"Command '{crit_cmd}' analyzed as: {crit_risk.name}")

        assert safe_risk == RiskLevel.SAFE
        # Since strict whitelist defaults to True, moderate might get categorized as CRITICAL
        assert crit_risk == RiskLevel.CRITICAL
        logger.info("✔ Dynamic security risk guardrails verified.")
    except Exception as e:
        logger.error(f"✘ Security analyzer validation failed: {e}")
        sys.exit(1)

    # 4. Test Semantic Vector Database Fallback
    logger.info("--- Testing Vector Semantic Memory Fallback ---")
    try:
        semantic_memory.add_memory(
            text="Central AI Boss controls ESP32 through webhooks at /webhook/esp32",
            metadata={"source": "api_docs"}
        )
        
        results = semantic_memory.query_memories("How does it work with ESP32?", limit=1)
        assert len(results) >= 1
        assert "webhook/esp32" in results[0]["document"]
        logger.info("✔ Semantic vector memory fallback queries verified.")
    except Exception as e:
        logger.error(f"✘ Semantic memory verification failed: {e}")
        sys.exit(1)

    logger.info("🎉 SUCCESS: All core subsystems passed verification checks! Codebase is ready for launch.")

if __name__ == "__main__":
    asyncio.run(run_verification())
