# DP_PATCHES — data-pipeline CVAT fork patch set (base: v2.83.0)

目标：CVAT 仅作标注画布；任务编排/指派/评审流转唯一事实源 =
data-pipeline annotation 服务（Portal 驱动，`dp-annotation` 服务账号执行）。

## 新增文件（隔离，不触上游逻辑）

| 文件 | 说明 |
|---|---|
| `cvat/apps/dpsso/` | SSO 桥 Django 应用：`/api/dp/sso?ticket=` 验 HMAC 一次性票据 → 建/更新用户（`dp-u-{uid}`，与 `dp-annotation` 服务账号命名空间隔离）+ 角色映射 → session login → 跳转 next。票据格式见 `dpsso/ticket.py`（dpsso1.b64json.b64hmac；exp≤60s；nonce 经 redis `cache.add` 单次消费）。角色：annotator→worker, qa→user, admin→admin（取最高）。密钥 env `CVAT_DP_SSO_SECRET`（空=禁用）。 |
| `cvat/apps/iam/rules/dp.rego` | `package utils` 扩展：`DP_SERVICE_ACCOUNT="dp-annotation"`、`is_dp_service_account`、`is_dp_restricted_{job,task,project}_scope`。 |

## 修改的上游文件（最小 diff）

| 文件 | 改动 |
|---|---|
| `cvat/apps/iam/permissions.py` | `build_iam_context` + OPA auth payload 增加 `username`（rego 按用户名识别服务账号；payload 侧 `getattr` 防御缺省）。 |
| `cvat/settings/base.py` | `INSTALLED_APPS += cvat.apps.dpsso`；`DP_SSO_SECRET = env CVAT_DP_SSO_SECRET`。 |
| `cvat/urls.py` | `path("api/dp/", include("cvat.apps.dpsso.urls"))`。 |
| `cvat/apps/engine/rules/jobs.rego` | `is_admin`/maintainer allow 追加 `not utils.is_dp_restricted_job_scope`；`{UPDATE_STAGE,UPDATE_ASSIGNEE}` 规则条件 `is_task_staff`→`utils.is_dp_service_account`。人类仍可 UPDATE_STATE（完成自己的 job）与标注。 |
| `cvat/apps/engine/rules/tasks.rego` | 同法：`is_admin`/maintainer/`{CREATE,IMPORT_BACKUP}`/`is_project_staff`/`is_task_owner` 规则追加 `not is_dp_restricted_task_scope`（CREATE/DELETE/UPDATE_ASSIGNEE）；新增服务账号 allow。 |
| `cvat/apps/engine/rules/projects.rego` | 同法（CREATE/DELETE/UPDATE_ASSIGNEE）。 |

## 语义

- **单点登录**：Portal "打开 CVAT" → BFF `GET /annotation/tasks/{id}/cvat-url` 签 60s 一次性票据 → `/api/dp/sso?ticket=`。长期 bearer 绝不入 URL。
- **单一事实源**：job assignee、job stage（acceptance）、task/project 建删仅 `dp-annotation` 可执行（rego 服务端强约束）；人类=标注+完成自己 job。
- **bootstrap**：部署侧建 `dp-annotation` 用户（admin 组即可执行全部受限动作——见 deploy/local/cvat）。

## 未做

- 前端隐藏 assignee/task-create UI（上游 UI 改动面大，rego 服务端已是权威；后续按最小 flag 加）。
- 镜像构建 `dp-v2.83.0-<sha>`（本批离线：server/ui 构建依赖 apt/pip/npm 网络）。
- opa test 用例（环境无 opa 二进制；规则经逐条 diff 复核）。
