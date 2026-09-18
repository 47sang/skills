---
name: remote-ops
description: 连接并操作远程服务器集群（医院内网、家用网关、测试服务器、公网入口），支持日志排查、Nginx 配置管理与验证、Docker 容器管理、项目部署。当用户需要查看远程服务器日志、修改 Nginx 端口转发配置、重启服务或排查部署问题时使用。
---

# 远程服务器运维

通过 SSH 别名连接 4 台服务器，实现日志排查、Nginx 配置管理、Docker 容器运维和项目部署的自动化操作。

> 最后探测时间：2026-09-18

## 服务器拓扑与资源

```
笔记本 (本地开发机)
    │
    ├── ub (192.168.5.13:22) ─── 家用核心网关枢纽
    │       ├── /opt/p2p/easytier-core  (P2P 客户端，连接 p2p 信令)
    │       ├── Nginx (宝塔面板管理，nginx -s reload)
    │       │     └── /www/server/panel/vhost/nginx/tcp/npc.conf (stream 转发)
    │       ├── GitLab 全家桶 (自托管)
    │       ├── Redis 6379
    │       └── 职责：P2P 中转枢纽，映射暴露其他节点端口
    │
    ├── cdc-ub (192.168.5.13:702) ─── 医院内网服务器（暂不操作）
    │       ├── P2P 隧道虚拟局域网 IP: 10.66.88.6
    │       ├── 映射到 ub 的 702 端口（SSH）、703（MySQL）、705（MSSQL）等
    │       ├── Nginx (标准安装)
    │       │     └── /etc/nginx/tcp/ 或 /etc/nginx/nginx.conf
    │       └── 职责：医院内网服务（HIS、追溯码、电子发票等）
    │
    ├── node (192.168.5.51:22) ─── 漫剧工具测试服务器（预部署阶段）
    │       ├── Nginx (Docker 容器内)
    │       ├── Docker 容器：app / worker / async-worker / beat / redis / postgres / nginx / new-api
    │       ├── 职责：公网测试演练，发现线上真实 bug
    │       └── 部署脚本：scripts/deploy.sh init / update
    │
    └── p2p (8.130.175.65:22) ─── 公网阿里云服务器
            ├── /opt/p2p/easytier-core  (P2P 信令/公网端点，IP: 10.66.88.1)
            ├── /opt/nps/  (NPS 内网穿透服务端，端口 598/599/600)
            ├── Nginx (标准安装，stream 模块)
            │     └── /etc/nginx/tcp/tcp.conf
            └── 职责：公网入口，EasyTier 信令 + NPS + Nginx 端口转发展示
```

### 🔗 核心访问链路

```
外部设备 ──→ p2p (公网 8.130.175.65:端口)
                │ EasyTier P2P 隧道（虚拟局域网 10.66.88.0/24）
                ▼
              ub (网关枢纽 10.66.88.4，Nginx stream 反向代理)
                │
        ┌───────┴───────┐
        ▼               ▼
    cdc-ub (10.66.88.6)   其他内网服务
```

### EasyTier P2P 网络节点

| 节点 | 虚拟 IP | 角色 | 延迟 | NAT 类型 | 隧道协议 |
|------|---------|------|------|---------|---------|
| ub (ub24) | 10.66.88.4 | 客户端 | - | PortRestricted | - |
| cdc-ub (cdc) | 10.66.88.6 | 客户端 | 16ms | Symmetric | UDP |
| p2p | 10.66.88.1 | 信令服务器 | 29ms | NoPat | TCP |

> EasyTier 版本：v2.1.0-e37aa0d8（三台一致），服务名 `tier.service`（`/etc/systemd/system/tier.service`），已配置开机自启。

### EasyTier 服务管理

```bash
# 查看状态
ssh ub "systemctl status tier"
ssh p2p "systemctl status tier"

# 重启服务
ssh ub "systemctl restart tier"
ssh p2p "systemctl restart tier"

# 查看日志
ssh ub "journalctl -u tier --no-pager -n 50"
ssh p2p "journalctl -u tier --no-pager -n 50"
```

> p2p 的 tier.service 配置了 `Restart=always` + `RestartSec=10`，崩溃后自动重启。ub 未配置自动重启。
> p2p 修改 service 文件后需执行 `systemctl daemon-reload` 再 restart。

## 服务器详细信息

### ub — 家用核心网关枢纽

| 项目 | 值 |
|------|---|
| 硬件 | AMD Ryzen 9 3900X 12 核 24 线程，20G 内存，76G 磁盘 |
| 系统 | Ubuntu 24，内核 6.8.0-139 |
| 运行时间 | 2+ 天（2026-09-18 探测时） |
| IP 地址 | 192.168.5.13（主）、192.168.5.6（辅）、10.66.88.4（tun0 P2P） |
| Docker | v28.3.0 |
| 宝塔面板 | 外网 `http://58.243.12.15:13183/a34a2ebb`，内网 `http://192.168.5.13:13183/a34a2ebb` |

**运行中的服务**：
- EasyTier P2P 客户端（连接 p2p:11010）
- Nginx（宝塔管理，stream 转发 + HTTP 反代）
- GitLab 全家桶（含 PostgreSQL、Redis、Prometheus、Alertmanager、Sidekiq）
- Redis（端口 6379）

**/opt 目录内容**：`4s`、`acloudmap`、`boot-0.1.jar`、`containerd`、`dl`、`easytier-linux-x86_64`、`gitlab`、`jdk`、`newp`、`npc`、`p2p`、`soft`、`www`、`xcx-1.0.0.jar`

**.bashrc 别名**：
```bash
alias ll='ls -lh --time-style="+%Y-%m-%d %H:%M" --color=auto'
alias lla='ls -lhA --time-style="+%Y-%m-%d %H:%M" --color=auto'
alias la='ls -A'
alias l='ls -CF'
alias p='bpytop'
alias peer='/opt/p2p/cli peer'    # 查看 P2P 节点列表
alias b='byobu'
alias opt='cd /opt && ll'
alias net='netstat -ntlp'
alias nt='nginx -t'               # 验证 Nginx 配置
alias nr='nginx -s reload'        # 重载 Nginx
```

**Nginx stream 转发规则**（`/www/server/panel/vhost/nginx/tcp/npc.conf`）：

当前活跃的转发规则：
| 监听端口 | 目标 | 用途 |
|---------|------|------|
| 605 | 10.66.88.6:5000 | HIS 接口互联网医院 |
| 702 | 10.66.88.6:22 | cdc-ub SSH |
| 703 | 10.66.88.6:3306 | cdc-ub MySQL |
| 705 | 10.66.88.6:1433 | HIS 数据库（从） |
| 716 | 10.66.88.6:30767 | cdc-ub 宝塔面板 |
| 720 | 10.66.88.6:30001 | HIS 追溯码接口 |
| 721 | 10.66.88.6:8849 | 集群控制台 |
| 722 | 10.66.88.6:30000 | 追溯码管理后台 |
| 723 | 10.66.88.6:1168 | 追溯码服务端 |
| 724 | 10.66.88.6:1170 | 追溯码服务端测试 |
| 725 | 10.66.88.6:30002 | 追溯码管理后台（测试环境） |
| 8086 | 10.66.88.6:18086 | 两定接口 |
| 800 | 192.168.5.18:3389 | 3900 远程桌面 |
| 802 | 192.168.5.11:3389 | VPN 虚拟机 1 |
| 803 | 192.168.5.55:3389 | VPN 虚拟机 2 |
| 804 | 192.168.5.56:3389 | VPN 虚拟机 3 |
| 9000 | 192.168.5.12:9000 | Mac MinIO |

> 600-604、606-607、706、710-712 等端口规则已注释（停用）。

### node — 漫剧测试服务器

| 项目 | 值 |
|------|---|
| 硬件 | AMD Ryzen 9 3900X 12 核，3.3G 内存，33G 磁盘 |
| 系统 | Ubuntu（内核 7.0.0-31） |
| 运行时间 | 1+ 天（2026-09-18 探测时） |
| IP | 192.168.5.51 |
| 数据目录 | `/data/` |

**Docker 容器**（全部 healthy）：

| 容器名 | 状态 | 端口 | 职责 |
|--------|------|------|------|
| backend-app-1 | Up (healthy) | 8000:8000 | FastAPI 应用 |
| backend-worker-1 | Up (healthy) | - | Celery worker（default 队列，并发 4） |
| backend-async-worker-1 | Up (healthy) | - | 异步 worker |
| backend-beat-1 | Up (healthy) | - | Celery beat 定时任务 |
| backend-redis-1 | Up 12h (healthy) | 6379 | Redis 缓存 |
| backend-postgres-1 | Up 12h (healthy) | 5432 | PostgreSQL 数据库 |
| backend-nginx-1 | Up 14h (healthy) | 80:80 | Nginx 反代 + 前端静态文件 |
| new-api | Up 13h (healthy) | 3000:3000 | new-api AI 网关 |

**数据目录结构**（`/data/`）：
| 目录 | 用途 |
|------|------|
| `/data/app/` | 应用源码（backend + .env + scripts） |
| `/data/postgres/` | PostgreSQL 数据 |
| `/data/redis/` | Redis 持久化数据 |
| `/data/logs/` | 应用日志 |
| `/data/frontend-dist/` | 前端构建产物（挂载到 nginx 容器） |
| `/data/nginx/` | Nginx 配置（`conf.d/nginx.conf`） |
| `/data/new-api/` | new-api 网关（含 docker-compose.yml） |
| `/data/new-api-data/` | new-api 数据（SQLite + 日志） |
| `/data/backups/` | 备份 |

**部署脚本**（`/data/app/scripts/`）：
```bash
ssh node "cd /data/app && scripts/deploy.sh init"     # 首次部署（构建镜像+启动+迁移）
ssh node "cd /data/app && scripts/deploy.sh update"    # 日常更新（rsync+前端+迁移+重启）
ssh node "cd /data/app && scripts/deploy.sh update --no-fe"  # 跳过前端构建
ssh node "cd /data/app && scripts/deploy.sh ps"        # 查看服务状态
ssh node "cd /data/app && scripts/deploy.sh logs app"  # 实时日志
```

> ⚠️ **Nginx 重启注意**：`deploy.sh`（日常更新）**不重启 Nginx 容器**。修改 Nginx 配置后必须用 `scripts/server-init.sh` 操作（它会显式 stop/start 重启 Nginx），或手动 `docker restart backend-nginx-1`。

**Docker Compose 文件**：`/data/app/backend/docker-compose.server.yml`

**Nginx 配置**：
- 生产配置：`/data/nginx/conf.d/nginx.conf`（挂载到 nginx 容器）
- 源码副本：`/data/app/backend/docker/nginx.conf`
- 使用 `resolver 127.0.0.11 valid=10s` 做动态 DNS 解析（规避容器重启 IP 漂移 502）
- 支持 API 反代、SSE 长连接、WebSocket、SPA 回退

**.bashrc 别名**：
```bash
alias ll='ls -lh --time-style="+%Y-%m-%d %H:%M" --color=auto'
alias lla='ls -lhA --time-style="+%Y-%m-%d %H:%M" --color=auto'
alias la='ls -A'
alias l='ls -CF'
alias p='bpytop'
alias peer='/opt/p2p/cli peer'    # 查看 P2P 节点列表（需安装 cli）
alias b='byobu'
alias opt='cd /opt && ll'
alias net='netstat -ntlp'
alias nt='nginx -t'
alias nr='nginx -s reload'
```

### p2p — 公网阿里云入口

| 项目 | 值 |
|------|---|
| 硬件 | Intel Xeon Platinum 8269CY 2 核，401M 内存，20G 磁盘 |
| 系统 | Ubuntu（内核 6.8.0-111） |
| 运行时间 | 112+ 天（极其稳定） |
| 公网 IP | 8.130.175.65 |
| 内网 IP | 172.26.129.203 |
| P2P IP | 10.66.88.1（tun0） |

**运行中的服务**：
- EasyTier P2P 信令服务器（端口 11010/11011/11012/15889）
- NPS 内网穿透服务端（端口 598 HTTP/599 bridge/600 管理）
- Nginx（stream + HTTP，端口 80/9000/4333）

**/opt 目录内容**：`dl`、`nps`、`p2p`、`safe`

**.bashrc 别名**：
```bash
alias ll='ls -lh --time-style="+%Y-%m-%d %H:%M" --color=auto'
alias lla='ls -lhA --time-style="+%Y-%m-%d %H:%M" --color=auto'
alias p='bpytop'
alias b='byobu'
alias log='tail -f /opt/4s/logs/log-info.log'  # 某服务日志
alias 4='cd /opt/4s && ll'
alias r='cd /opt/red && ll'
alias opt='cd /opt && ll'
alias net='netstat -ntlp'
alias nt='nginx -t'
alias nr='nginx -s reload'
```

**Nginx stream 配置**（`/etc/nginx/tcp/tcp.conf`）：
```nginx
# mac minio（当前唯一活跃规则）
server {
    listen 9000;
    proxy_connect_timeout 10s;
    proxy_timeout 300s;
    proxy_pass 10.66.88.4:9000;  # 转发到 ub 的 Mac MinIO
}
```

> 有备份文件 `tcp.conf.bak`。新增转发规则时在此文件追加 server 块。

## SSH 连接

所有服务器均使用 `ssh <别名>` 直连，密钥已配置免密登录：

```bash
ssh ub          # 家用网关枢纽（宝塔面板）
ssh cdc-ub      # 医院内网（经 ub P2P 映射，端口 702）
ssh node        # 漫剧测试服务器
ssh p2p         # 公网阿里云
```

> cdc-ub 的 SSH 流量走 ub 的 P2P 隧道转发，延迟约 16ms。

## Nginx 配置管理

### 配置验证与重载流程

```bash
# 验证配置语法
ssh <别名> "nginx -t"

# 验证通过 → 平滑重载
ssh <别名> "nginx -s reload"

# 验证失败 → 查看错误详情
ssh <别名> "nginx -t 2>&1"
```

### 自动化端口转发配置

当需要将内网服务端口暴露到公网时，修改链路涉及两台服务器：

1. **p2p**（公网入口）：在 `/etc/nginx/tcp/tcp.conf` 添加 stream 规则
2. **ub**（网关枢纽）：在 `/www/server/panel/vhost/nginx/tcp/npc.conf` 添加 stream 规则

操作步骤：
1. 读取两台服务器当前的 Nginx stream 配置
2. 分别添加新的 server 块
3. 分别验证配置语法（`nginx -t`）
4. 分别平滑重载（`nginx -s reload`）
5. 通过公网端口测试连通性

> ub 使用宝塔面板管理 Nginx，手动修改配置文件后，注意宝塔面板操作可能覆盖配置。

### 各服务器 Nginx 配置路径速查

| 服务器 | Nginx 类型 | 配置路径 | 重启命令 |
|--------|-----------|---------|---------|
| ub | 宝塔面板管理 | `/www/server/nginx/conf/nginx.conf`，stream 在 `/www/server/panel/vhost/nginx/tcp/npc.conf` | `nginx -s reload` |
| cdc-ub | 标准安装 | `/etc/nginx/nginx.conf`，stream 在 `/etc/nginx/tcp/` | `nginx -t && nginx -s reload` |
| node | Docker 容器 | `/data/nginx/conf.d/nginx.conf`（挂载），源码 `/data/app/backend/docker/nginx.conf` | `server-init.sh`（显式 stop/start）或 `docker restart backend-nginx-1`（deploy.sh 不重启 Nginx） |
| p2p | 标准安装 | `/etc/nginx/nginx.conf`，stream 在 `/etc/nginx/tcp/tcp.conf` | `nginx -t && nginx -s reload` |

## 日志排查流程

### 通用排查步骤

1. **确认服务状态**：容器是否运行、进程是否存在
2. **查看最近日志**：定位错误信息和时间线
3. **检查配置文件**：语法是否正确、配置是否生效
4. **验证网络连通**：端口是否可达、P2P 隧道是否正常

### 常用日志路径速查

| 服务器 | 日志类型 | 路径 / 命令 |
|--------|---------|------------|
| ub | Nginx 错误 | `/www/server/nginx/logs/error.log` |
| ub | Nginx 访问 | `/www/server/nginx/logs/access.log` |
| ub | GitLab | `gitlab-ctl tail` |
| cdc-ub | Nginx 错误 | `/var/log/nginx/error.log` |
| node | 后端应用 | `docker logs --tail 200 backend-app-1` |
| node | Celery worker | `docker logs --tail 200 backend-worker-1` |
| node | 异步 worker | `docker logs --tail 200 backend-async-worker-1` |
| node | Beat 定时任务 | `docker logs --tail 200 backend-beat-1` |
| node | Nginx | `docker logs --tail 200 backend-nginx-1` |
| node | new-api 网关 | `docker logs --tail 200 new-api` |
| node | 应用日志文件 | `/data/logs/`（挂载到宿主机） |
| p2p | Nginx 错误 | `/var/log/nginx/error.log` |

### node 服务器专项排查

node 是漫剧工具的测试服务器，排查重点：
- **后端报错**：`docker logs --tail 200 backend-app-1`
- **任务卡住**：`docker logs --tail 200 backend-worker-1`
- **定时任务异常**：`docker logs --tail 200 backend-beat-1`
- **AI 网关问题**：`docker logs --tail 200 new-api`
- **前端白屏**：检查 `backend-nginx-1` 日志和 `/data/frontend-dist/` 是否有文件
- **数据库问题**：`docker exec -it backend-postgres-1 psql -U manju`
- **部署状态**：`scripts/deploy.sh ps` 查看各容器运行状态

### 线上问题修复流程

当用户说「排查线上问题」「去线上找日志」「修复线上报错」时：
1. 连接 node 服务器查看应用日志（`docker logs`）
2. 定位报错信息和堆栈
3. 回到本机项目代码中修复对应问题
4. 通过 `scripts/deploy.sh update` 同步到 node 验证

## 注意事项

- **cdc-ub 是医院内网**：操作时注意数据安全，不传输敏感数据到公网服务器
- **ub 的宝塔面板**：Nginx 配置可能被面板操作覆盖，重要修改建议在面板中也同步更新
- **node 的 Docker Nginx**：Nginx 配置修改通过项目部署脚本管理，不要直接进容器改
- **p2p 资源有限**：仅 2 核 401M 内存，不要在上面跑重任务
- **EasyTier 已配置 systemd**：服务名 `tier.service`，ub/p2p 均已 enabled 开机自启。p2p 额外配了 `Restart=always` 自动恢复
- **用户偏好 /opt 目录**：常用软件装在 `/opt/` 下，常用命令别名配在 `/root/.bashrc`
