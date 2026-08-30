#!/bin/bash
cd "$(dirname "$0")"
uv run --frozen mcp_server.py
