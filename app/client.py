import os
import time
import logging
import tigerbeetle as tb
from dotenv import load_dotenv

load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("TigerBeetleClient")

CLUSTER_ID = int(os.getenv("TB_CLUSTER_ID", "0"))
REPLICA_ADDRESSES = os.getenv("TB_REPLICA_ADDRESSES", "3000")

class TigerBeetleClient:
    def __init__(self):
        logger.info(f"Initializing TigerBeetle client for cluster {CLUSTER_ID}...")
        try:
            self.client = tb.ClientSync(CLUSTER_ID, REPLICA_ADDRESSES)
            logger.info("TigerBeetle client initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize TigerBeetle client: {e}")
            raise

    def _execute(self, op_name, func, *args):
        start_time = time.perf_counter()
        try:
            result = func(*args)
            latency = (time.perf_counter() - start_time) * 1000
            logger.info(f"Operation {op_name} executed in {latency:.2f}ms")
            return result
        except Exception as e:
            logger.error(f"Operation {op_name} failed: {e}")
            raise

    def create_accounts(self, accounts):
        return self._execute("create_accounts", self.client.create_accounts, accounts)

    def lookup_accounts(self, ids):
        return self._execute("lookup_accounts", self.client.lookup_accounts, ids)

    def create_transfers(self, transfers):
        return self._execute("create_transfers", self.client.create_transfers, transfers)

    def lookup_transfers(self, ids):
        return self._execute("lookup_transfers", self.client.lookup_transfers, ids)

    def get_account_balances(self, filter):
        return self._execute("get_account_balances", self.client.get_account_balances, filter)

    def get_account_transfers(self, filter):
        return self._execute("get_account_transfers", self.client.get_account_transfers, filter)

    def query_accounts(self, filter):
        return self._execute("query_accounts", self.client.query_accounts, filter)

    def query_transfers(self, filter):
        return self._execute("query_transfers", self.client.query_transfers, filter)

    def close(self):
        logger.info("Closing TigerBeetle client...")
        self.client.close()

# Singleton instance
tb_client = None

def get_client():
    global tb_client
    if tb_client is None:
        tb_client = TigerBeetleClient()
    return tb_client
