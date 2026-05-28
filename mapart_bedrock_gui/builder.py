import asyncio
import logging
import math
import traceback
from pathlib import Path
from typing import Optional

import adorable
from bedrock.consts import NAME
from bedrock.context import PlayerMessageContext, ReadyContext
from bedrock.ext import ui
from bedrock.server import Server

from .processor import process_image, MAP_TILE
from .coordinates import load_coords, save_coords, add_coord, is_coord_used

logger = logging.getLogger("mapart")

# Blocks that fall with gravity in Bedrock
GRAVITY_BLOCKS = {
    "sand", "red_sand", "gravel",
    "black_concrete_powder", "blue_concrete_powder", "brown_concrete_powder",
    "cyan_concrete_powder", "gray_concrete_powder", "green_concrete_powder",
    "light_blue_concrete_powder", "light_gray_concrete_powder",
    "lime_concrete_powder", "magenta_concrete_powder", "orange_concrete_powder",
    "pink_concrete_powder", "purple_concrete_powder", "red_concrete_powder",
    "white_concrete_powder", "yellow_concrete_powder",
}

RED = adorable.Color8bit.from_name("red")
GREEN = adorable.Color8bit.from_name("green")
BLUE = adorable.Color8bit.from_name("blue")
YELLOW = adorable.Color8bit.from_name("yellow")
PREFIX = "#"

DIMENSIONS = {"overworld", "nether", "end"}


class MapartBuilder:
    def __init__(
        self,
        root_dir: Path,
        palette: str,
        dither: str,
        staircasing: str,
        give_mode: bool = False,
        color_mode: str = "lab",
    ):
        self.root_dir = root_dir
        self.palette = palette
        self.dither = dither
        self.staircasing = staircasing
        self.give_mode = give_mode
        self.color_mode = color_mode
        self.data_dir = root_dir / ".mapart"
        self.data_dir.mkdir(exist_ok=True)
        self.server = Server()

    def launch(self, address: str, port: int):
        load_coords(self.data_dir)

        @self.server.server_event
        async def ready(ctx: ReadyContext):
            print(f"{GREEN.bg: MapArt for Bedrock }")
            print(f"{BLUE.fg: LIVE} at {YELLOW.bg: {ctx.host}:{ctx.port} }")
            print(f"Share directory: {self.root_dir}")
            print(f"Palette: {self.palette} | Dither: {self.dither} | Staircasing: {self.staircasing}")
            print(f"Commands: #build <image> [#build <image> --tile=N] | #coords | #help")

        @self.server.game_event
        async def player_message(ctx: PlayerMessageContext):
            if ctx.sender == NAME:
                return
            message = ctx.message.strip()
            if not message.startswith(PREFIX):
                return
            parts = message.removeprefix(PREFIX).split()
            if not parts:
                return
            cmd = parts[0].lower()
            args = parts[1:]
            try:
                if cmd == "build":
                    await self._handle_build(ctx, args)
                elif cmd == "coords":
                    await self._handle_coords(ctx, args)
                elif cmd == "testblock":
                    await self._handle_testblock(ctx, args)
                elif cmd == "help":
                    await self._handle_help(ctx)
                else:
                    await ctx.reply(ui.red(f"Unknown command. Use #help"))
            except Exception as e:
                await ctx.reply(ui.red(f"Error: {e}"))
                print(f"{RED.fg:ERROR:} {e}")
                traceback.print_exc()

        self.server.start(address, port)

    async def _handle_build(self, ctx, args):
        if not args:
            await ctx.reply(ui.red("Usage: #build <image_path> [--x=X] [--z=Z] [--y=Y] [--tile=N]"))
            return

        image_rel = args[0]
        path = self.root_dir / image_rel

        if ".." in path.parts:
            await ctx.reply(ui.red("Error: Cannot use `..` in path"))
            return
        if not path.exists():
            alt = self.root_dir / f"{Path(image_rel).stem}_mapart.png"
            if alt.exists():
                path = alt
            else:
                await ctx.reply(ui.red(f"Error: {image_rel} not found"))
                return
        if not path.is_file():
            await ctx.reply(ui.red(f"Error: {image_rel} is not a file"))
            return

        origin_x = origin_z = 0
        build_y = -1
        tile_idx = -1

        for arg in args[1:]:
            if arg.startswith("--x="):
                origin_x = int(arg.split("=")[1])
            elif arg.startswith("--z="):
                origin_z = int(arg.split("=")[1])
            elif arg.startswith("--y="):
                build_y = int(arg.split("=")[1])
            elif arg.startswith("--tile="):
                tile_idx = int(arg.split("=")[1])

        # use player position as default origin when --x/--z omitted
        has_x = any(a.startswith("--x=") for a in args[1:])
        has_z = any(a.startswith("--z=") for a in args[1:])
        if not has_x and not has_z:
            player_data = ctx.data.get("player", {})
            pos = player_data.get("position", {})
            if pos.get("x") is not None:
                origin_x, origin_z = int(pos["x"]), int(pos["z"])

        await ctx.reply(ui.green(f"Processing {image_rel}..."))

        loop = asyncio.get_event_loop()
        blocks, img_w, img_h = await loop.run_in_executor(
            None, process_image,
            str(path), self.palette, self.dither, self.staircasing, self.color_mode,
        )

        tiles_x = img_w // MAP_TILE
        tiles_z = img_h // MAP_TILE
        total_tiles = tiles_x * tiles_z

        if total_tiles > 1 and tile_idx < 0:
            await ctx.reply(
                ui.green(
                    f"Image is {img_w}x{img_h} ({total_tiles} tiles). "
                    f"Use #build {image_rel} --tile=N for a specific tile (0-{total_tiles - 1}), "
                    f"or I'll build all tiles now."
                )
            )

        if tile_idx >= 0:
            await self._build_tile(ctx, blocks, tile_idx, tiles_x, origin_x, origin_z, build_y, image_rel)
        else:
            for ti in range(total_tiles):
                await self._build_tile(ctx, blocks, ti, tiles_x, origin_x, origin_z, build_y, image_rel)

    async def _build_tile(self, ctx, blocks, tile_idx, tiles_x, origin_x, origin_z, build_y, image_rel):
        tile_z = tile_idx // tiles_x
        tile_x = tile_idx % tiles_x

        tile_blocks = []
        for x, z, dy, block_name, tone, _ in blocks:
            tx = x // MAP_TILE
            tz = z // MAP_TILE
            if tx == tile_x and tz == tile_z:
                tile_blocks.append((x % MAP_TILE, z % MAP_TILE, dy, block_name, tone))

        if not tile_blocks:
            await ctx.reply(ui.red(f"Tile {tile_idx} is empty"))
            return

        tile_ox = origin_x + tile_x * MAP_TILE
        tile_oz = origin_z + tile_z * MAP_TILE

        unique_blocks = sorted({b[3] for b in tile_blocks})
        logger.info(f"Tile {tile_idx}: {len(tile_blocks)} blocks, {len(unique_blocks)} unique types")
        logger.info(f"Blocks: {', '.join(unique_blocks)}")
        await ctx.reply(
            ui.green(
                f"Tile {tile_idx}: placing {len(tile_blocks)} blocks "
                f"({len(unique_blocks)} types) at ({tile_ox}, {build_y}, {tile_oz})..."
            )
        )

        if self.give_mode:
            given = set()
            for _, _, _, block_name, _ in tile_blocks:
                if block_name not in given:
                    await ctx.server.run(f"give @s {block_name} 64", wait=False)
                    given.add(block_name)
            await ctx.reply(ui.green(f"Gifted {len(given)} block types"))
            await asyncio.sleep(0.5)

        await ctx.server.run(f"inputpermission set {ctx.sender} movement disabled")

        try:
            await self._place_blocks(ctx, tile_blocks, tile_ox, tile_oz, build_y)
            await ctx.reply(ui.green(f"Tile {tile_idx} done! ({len(tile_blocks)} blocks)"))
        except Exception as e:
            await ctx.reply(ui.red(f"Tile {tile_idx} failed: {e}"))
            raise
        finally:
            await ctx.server.run(f"inputpermission set {ctx.sender} movement enabled")

    async def _place_blocks(self, ctx, blocks, origin_x, origin_z, build_y):
        unique_blocks = sorted({b[3] for b in blocks})
        logger.info(f"Placing {len(blocks)} blocks ({len(unique_blocks)} unique types)")
        logger.info(f"Blocks: {', '.join(unique_blocks)}")

        tickingarea = f"mapart_tile_{origin_x}_{origin_z}"
        await ctx.server.run(
            f"tickingarea add {origin_x} {build_y} {origin_z} "
            f"{origin_x + MAP_TILE} {build_y} {origin_z + MAP_TILE} "
            f"{tickingarea}"
        )

        # Phase 0: place support blocks under gravity-affected blocks
        support_done = set()
        support_commands = []
        for x, z, dy, block_name, tone in blocks:
            if block_name in GRAVITY_BLOCKS:
                bx = origin_x + x
                bz = origin_z + z
                by = build_y + dy
                key = (bx, bz)  # one support per column regardless of y
                if key not in support_done:
                    support_done.add(key)
                    support_commands.append(f"setblock {bx} {by - 1} {bz} stone")

        if support_commands:
            logger.info(f"Placing {len(support_commands)} support blocks for gravity blocks")
            for i in range(0, len(support_commands), 100):
                batch = support_commands[i:i + 100]
                tasks = [ctx.server.run(cmd, wait=True) for cmd in batch]
                await asyncio.gather(*tasks)

        # Phase 1: place all map art blocks
        commands = []
        for x, z, dy, block_name, tone in blocks:
            bx = origin_x + x
            bz = origin_z + z
            by = build_y + dy
            commands.append(f"setblock {bx} {by} {bz} {block_name}")

        batch_size = 100
        total = len(commands)
        failed_commands = []
        for i in range(0, total, batch_size):
            batch = commands[i:i + batch_size]
            tasks = [ctx.server.run(cmd, wait=True) for cmd in batch]
            results = await asyncio.gather(*tasks)
            for cmd, resp in zip(batch, results):
                if resp is not None and not resp.ok:
                    failed_commands.append((cmd, resp.message, resp.status))
            progress = min(i + batch_size, total)
            pct = math.floor(progress / total * 100)
            status = f"§aProgress: {pct}% ({progress}/{total})"
            if failed_commands:
                status += f" §c{len(failed_commands)} failed"
            await ctx.server.run(
                f"title @s actionbar {status}",
                wait=False,
            )

        if failed_commands:
            logger.warning(f"WARNING: {len(failed_commands)} setblock commands failed!")
            for cmd, msg, status in failed_commands[:20]:
                logger.warning(f"  FAILED: {cmd} -> status={status}, msg={msg}")
            await ctx.reply(
                ui.red(f"WARNING: {len(failed_commands)} blocks failed to place "
                       f"(showing first 20 in console)")
            )

        await ctx.server.run(f"tickingarea remove {tickingarea}")

    async def _handle_testblock(self, ctx, args):
        if not args:
            await ctx.reply(ui.red("Usage: #testblock <block_name>"))
            return
        block_name = args[0]
        player_data = ctx.data.get("player", {})
        pos = player_data.get("position", {})
        x = int(pos.get("x", 0))
        y = int(pos.get("y", 0))
        z = int(pos.get("z", 0))
        await ctx.reply(ui.green(f"Testing block '{block_name}' at player position..."))
        resp = await ctx.server.run(f"setblock {x} {y + 5} {z} {block_name}", wait=True)
        if resp is None:
            await ctx.reply(ui.red(f"No response for '{block_name}'"))
            return
        if resp.ok:
            await ctx.reply(ui.green(f"OK: '{block_name}' placed at ({x}, {y + 5}, {z})"))
        else:
            await ctx.reply(
                ui.red(f"FAIL: '{block_name}' -> {resp.message} (status={resp.status})")
            )

    async def _handle_coords(self, ctx, args):
        if not args:
            await ctx.reply(
                ui.green("Usage: #coords saveat <x> <z> [name] | #coords clear | #coords list")
            )
            return
        sub = args[0].lower()
        if sub == "saveat":
            if len(args) < 3:
                await ctx.reply(ui.red("Usage: #coords saveat <x> <z> [name]"))
                return
            x = int(args[1])
            z = int(args[2])
            name = " ".join(args[3:]) if len(args) > 3 else ""
            entry = add_coord(self.data_dir, x, 64, z, name)
            await ctx.reply(ui.green(f"Saved coord: ({x}, {z}) as '{entry['name']}'"))
        elif sub == "list":
            from .coordinates import USED_COORDS
            if not USED_COORDS:
                await ctx.reply(ui.green("No saved coordinates"))
            else:
                lines = [f"§aSaved coords ({len(USED_COORDS)}):"]
                for c in USED_COORDS:
                    lines.append(f"  {c['name']}: ({c['x']}, {c['z']})")
                await ctx.reply("\n".join(lines))
        elif sub == "clear":
            from .coordinates import USED_COORDS
            USED_COORDS.clear()
            save_coords(self.data_dir)
            await ctx.reply(ui.green("Cleared all saved coordinates"))

    async def _handle_help(self, ctx):
        help_text = (
            "§aMapArt for Bedrock§r\n"
            f"§e#build <image> [--x=X] [--z=Z] [--y=Y]§r\n"
            f"  Default origin is (0, -1, 0) if --x/--z/--y omitted\n"
            f"  §7Example: #build image.png --x=100 --z=200 --y=64§r\n"
            f"§e#coords saveat <x> <z> [name]§r - Save location\n"
            f"§e#coords list§r - List saved locations\n"
            f"§e#coords clear§r - Clear saved locations\n"
            f"§e#testblock <name>§r - Test if a block name works\n"
            f"§e#help§r - Show this help"
        )
        await ctx.reply(help_text)
