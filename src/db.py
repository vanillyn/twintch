import aiosqlite

DB_PATH = "bot.db"


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS streamers (
                twitch_user_id   TEXT    PRIMARY KEY,
                twitch_username  TEXT    NOT NULL,
                discord_channel_id INTEGER NOT NULL DEFAULT 0,
                subscription_id  TEXT    NOT NULL DEFAULT '',
                ping_role_id     INTEGER NOT NULL DEFAULT 0,
                custom_message   TEXT    NOT NULL DEFAULT '{user} is live',
                footer_message   TEXT    NOT NULL DEFAULT '{followers} followers',
                accent_color     INTEGER NOT NULL DEFAULT 9442302
            )
        """)
        await db.commit()


async def add_streamer(
    twitch_user_id: str,
    twitch_username: str,
    discord_channel_id: int,
) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT OR IGNORE INTO streamers
               (twitch_user_id, twitch_username, discord_channel_id)
               VALUES (?, ?, ?)""",
            (twitch_user_id, twitch_username, discord_channel_id),
        )
        await db.commit()


async def update_streamer(twitch_user_id: str, **kwargs: str | int) -> None:
    if not kwargs:
        return
    cols = ", ".join(f"{k} = ?" for k in kwargs)
    vals: list[str | int] = [*kwargs.values(), twitch_user_id]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE streamers SET {cols} WHERE twitch_user_id = ?", vals)
        await db.commit()


async def get_streamer(twitch_user_id: str) -> aiosqlite.Row | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM streamers WHERE twitch_user_id = ?", (twitch_user_id,)
        ) as cursor:
            return await cursor.fetchone()


async def get_streamer_by_username(username: str) -> aiosqlite.Row | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM streamers WHERE LOWER(twitch_username) = LOWER(?)",
            (username,),
        ) as cursor:
            return await cursor.fetchone()


async def get_all_streamers() -> list[aiosqlite.Row]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM streamers") as cursor:
            return await cursor.fetchall()


async def remove_streamer(twitch_user_id: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM streamers WHERE twitch_user_id = ?", (twitch_user_id,)
        )
        await db.commit()
