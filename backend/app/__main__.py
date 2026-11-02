"""使用 python -m app --env dev 或 prod 启动服务。"""
import argparse
import os

def main():
    """选择运行环境后启动 Uvicorn。"""
    parser = argparse.ArgumentParser(description="启动 NexusOps 后端")
    parser.add_argument("--env", choices=("dev", "test", "prod"), default="dev")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8887)
    args = parser.parse_args()
    os.environ["NEXUSOPS_ENV"] = args.env
    import uvicorn
    uvicorn.run("app.main:app", host=args.host, port=args.port, reload=args.env == "dev")

if __name__ == "__main__":
    main()
