import base64
import json

from discord.ext import commands
from google.cloud import firestore
from google.oauth2 import service_account


class Firestore(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        credentials = service_account.Credentials.from_service_account_info(
            json.loads(base64.b64decode(self.bot.get_env_value("firestore")))
        )

        self.db = firestore.AsyncClient("quantum-database", credentials)

    # noinspection PyTypeChecker
    async def get(self, *walk):
        current = self.db
        snapshot = None
        original = self.db

        for p in walk:
            p = str(p)
            if isinstance(current, (firestore.AsyncClient, firestore.AsyncDocumentReference)):
                current = current.collection(p)
                original = original.collection(p)
            else:
                document = current.document(p)
                original = original.document(p)
                snapshot = await document.get()
                if snapshot.exists:
                    print(p, "exists")
                    current = document
                else:
                    print(p, "does not exist")
                    current = current.document("?")
                    snapshot = await current.get()

        return snapshot.to_dict(), original


def setup(bot):
    bot.add_cog(Firestore(bot))
