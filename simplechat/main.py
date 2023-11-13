from aiohttp import web, WSMsgType
from aiohttp.web_request import Request
import datetime
import hashlib
import asyncio
import jinja2
import base64
import os

routes = web.RouteTableDef()


def render(template_name: str, context: dict) -> str:
    template = env.get_template(template_name)
    return template.render(context)


@routes.post("/login")
async def login(request: Request) -> web.StreamResponse:
    data = await request.post()
    username = data.get("username")
    if not username:
        raise web.HTTPBadRequest
    resp = web.Response(text=render("form.j2", {}), content_type="text/html")
    resp.set_cookie("username", username)
    return resp


@routes.get("/")
async def index(request: Request) -> web.StreamResponse:
    username = request.cookies.get("username")
    return web.Response(
        text=render("index.j2", {"username": username}), content_type="text/html"
    )


@routes.post("/send")
async def send(request: Request) -> web.StreamResponse:
    data = await request.post()
    message = data.get("message")
    image = data.get("file")
    dataurl = None
    if image:
        filename = image.filename
        binary_fc = image.file.read()
        base64_utf8_str = base64.b64encode(binary_fc).decode("utf-8")
        ext = filename.split(".")[-1]
        dataurl = f"data:image/{ext};base64,{base64_utf8_str}"

    username = request.cookies.get("username")
    if not username:
        raise web.HTTPBadRequest
    color = int(hashlib.sha1(username.encode("utf-8")).hexdigest(), 16) % 10
    ltime = datetime.datetime.now()
    time = ltime.strftime("%H:%M")

    if not (message or image):
        raise web.HTTPBadRequest

    tasks = []
    for ws in app["websockets"]:
        tasks.append(
            ws.send_str(
                render(
                    "message.j2",
                    {
                        "message": message,
                        "username": username,
                        "color": color,
                        "image": dataurl,
                        "time": time,
                    },
                )
            )
        )
    await asyncio.gather(*tasks)

    return web.Response()


@routes.get("/ws")
async def ws(request: Request) -> web.WebSocketResponse:
    ws = web.WebSocketResponse(autoping=True, heartbeat=5.0)
    await ws.prepare(request)
    app["websockets"].append(ws)
    async for msg in ws:
        if msg.type == web.WSMsgType.TEXT:
            if msg.data == "close":
                await ws.close()
    app["websockets"].remove(ws)
    return ws


async def init_app() -> web.Application:
    global env, app
    app = web.Application(client_max_size=float("inf"))
    app["websockets"] = []
    template_dir = os.path.join(os.path.dirname(__file__), "templates")
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(template_dir), autoescape=True
    )
    app.add_routes(routes)
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    app.router.add_static("/static", static_dir)
    return app


def main():
    app = init_app()
    web.run_app(app)


if __name__ == "__main__":
    main()
