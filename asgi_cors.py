import fnmatch
from functools import wraps


def asgi_cors_decorator(allow_all=False, hosts=None, host_wildcards=None):
    hosts = hosts or []
    host_wildcards = host_wildcards or []

    # We need hosts and host_wildcards to be b""
    hosts = set(h.encode("utf8") if isinstance(h, str) else h for h in hosts)
    host_wildcards = [
        h.encode("utf8") if isinstance(h, str) else h for h in host_wildcards
    ]

    if any(h.endswith(b"/") for h in (hosts or [])) or any(
        h.endswith(b"/") for h in (host_wildcards or [])
    ):
        assert False, "Error: CORS origin rules should never end in a /"

    def _asgi_cors_decorator(app):
        @wraps(app)
        async def app_wrapped_with_cors(scope, recieve, send):
            async def wrapped_send(event):
                if event["type"] == "http.response.start":
                    original_headers = event.get("headers") or []
                    access_control_allow_origin = None
                    if allow_all:
                        access_control_allow_origin = b"*"
                    elif hosts or host_wildcards:
                        incoming_origin = dict(scope.get("headers") or []).get(
                            b"origin"
                        )
                        if incoming_origin:
                            matches_hosts = incoming_origin in hosts
                            matches_wildcards = any(
                                fnmatch.fnmatch(incoming_origin, host_wildcard)
                                for host_wildcard in host_wildcards
                            )
                            if matches_hosts or matches_wildcards:
                                access_control_allow_origin = incoming_origin
                    if access_control_allow_origin is not None:
                        # Construct a new event with new headers
                        event = {
                            "type": "http.response.start",
                            "status": event["status"],
                            "headers": [
                                p
                                for p in original_headers
                                if p[0] != b"access-control-allow-origin"
                            ]
                            + [
                                [
                                    b"access-control-allow-origin",
                                    access_control_allow_origin,
                                ]
                            ],
                        }
                await send(event)

            await app(scope, recieve, wrapped_send)

        return app_wrapped_with_cors

    return _asgi_cors_decorator


def asgi_cors(app, allow_all=False, hosts=None, host_wildcards=None):
    return asgi_cors_decorator(allow_all, hosts, host_wildcards)(app)
