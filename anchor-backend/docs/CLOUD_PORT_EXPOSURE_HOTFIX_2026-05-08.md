# CLOUD_PORT_EXPOSURE_HOTFIX_2026-05-08

## 1. 结论

云主机端口暴露止血已完成。

已通过 `DOCKER-USER` 规则阻断公网进入以下端口：

- backend: `8000`
- postgres: `5432`
- redis: `6379`

IPv4 与 IPv6 均已覆盖。

---

## 2. 已确认的运行态规则

IPv4：

```text
-A DOCKER-USER -i eth0 -p tcp -m tcp --dport 6379 -j DROP
-A DOCKER-USER -i eth0 -p tcp -m tcp --dport 5432 -j DROP
-A DOCKER-USER -i eth0 -p tcp -m tcp --dport 8000 -j DROP
```

IPv6：

```text
-A DOCKER-USER -i eth0 -p tcp -m tcp --dport 6379 -j DROP
-A DOCKER-USER -i eth0 -p tcp -m tcp --dport 5432 -j DROP
-A DOCKER-USER -i eth0 -p tcp -m tcp --dport 8000 -j DROP
```

---

## 3. 已确认的服务状态

backend 本机健康检查正常：

```text
curl -sS http://127.0.0.1:8000/health
{"ok":true}
```

nginx 本机入口正常：

```text
curl -i http://127.0.0.1/healthz
HTTP/1.1 200 OK

ok
```

容器状态正常：

* backend: Up
* worker: Up
* postgres: Up
* redis: Up

---

## 4. 已确认的持久化状态

`netfilter-persistent` 已启用：

```text
enabled
Active: active (exited)
status=0/SUCCESS
```

规则已写入：

* `/etc/iptables/rules.v4`
* `/etc/iptables/rules.v6`

---

## 5. 当前遗留问题

`docker compose ps` 仍显示以下公网绑定：

```text
0.0.0.0:8000->8000/tcp
0.0.0.0:5432->5432/tcp
0.0.0.0:6379->6379/tcp
[::]:8000->8000/tcp
[::]:5432->5432/tcp
[::]:6379->6379/tcp
```

这说明 compose 层仍未最终收口。

当前 `DOCKER-USER` 防火墙规则属于已持久化的安全止血措施。

后续如继续修复，应单独开任务，将 compose 端口绑定改为 `127.0.0.1`，不得与本次封板混做。

---

## 6. 禁止事项

本次封板后，禁止顺手执行：

* `docker compose down`
* `docker compose up`
* `reboot`
* 修改 `docker-compose.yml`
* 修改 nginx
* 修改 env
* 修改 backend / worker / risk 代码

---

## 7. 回滚方法

如需回滚本次防护规则，执行：

```bash
iptables -D DOCKER-USER -i eth0 -p tcp --dport 6379 -j DROP
iptables -D DOCKER-USER -i eth0 -p tcp --dport 5432 -j DROP
iptables -D DOCKER-USER -i eth0 -p tcp --dport 8000 -j DROP

ip6tables -D DOCKER-USER -i eth0 -p tcp --dport 6379 -j DROP
ip6tables -D DOCKER-USER -i eth0 -p tcp --dport 5432 -j DROP
ip6tables -D DOCKER-USER -i eth0 -p tcp --dport 8000 -j DROP

netfilter-persistent save
```

---

## 8. 封板状态

状态：`HOTFIX_ACCEPTED`

日期：`2026-05-08`

范围：仅云主机端口暴露止血记录。
