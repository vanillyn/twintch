import aiosqlite

DB_PATH = "bot.db"


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS streamers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                twitch_user_id TEXT NOT NULL UNIQUE,
                twitch_username TEXT NOT NULL,
                discord_channel_id INTEGER NOT NULL,
                subscription_id TEXT,
                ping_everyone INTEGER DEFAULT 0
            )
        """)
        await db.commit()


async def add_streamer(twitch_user_id, twitch_username, discord_channel_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT OR IGNORE INTO streamers (twitch_user_id, twitch_username, discord_channel_id)
            VALUES (?, ?, ?)
        """,
            (twitch_user_id, twitch_username, discord_channel_id),
        )
        await db.commit()


async def set_subscription_id(twitch_user_id, subscription_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE streamers SET subscription_id = ? WHERE twitch_user_id = ?",
            (subscription_id, twitch_user_id),
        )
        await db.commit()


async def get_streamer_by_user_id(twitch_user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM streamers WHERE twitch_user_id = ?", (twitch_user_id,)
        ) as cursor:
            return await cursor.fetchone()


async def get_all_streamers():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM streamers") as cursor:
            return await cursor.fetchall()


async def remove_streamer(twitch_user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM streamers WHERE twitch_user_id = ?", (twitch_user_id,)
        )
        await db.commit()
