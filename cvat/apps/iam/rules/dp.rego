# data-pipeline 扩展（DP_PATCHES.md）：标注任务编排的唯一事实源 =
# data-pipeline annotation 服务账号。人类（含 admin）不得再改
# job assignee / job stage / task·project 建删——指派与评审流转
# 全部由 Portal/annotation 服务驱动，经服务账号 API 执行。
package utils

import rego.v1

DP_SERVICE_ACCOUNT := "dp-annotation"

is_dp_service_account if {
	input.auth.user.username == DP_SERVICE_ACCOUNT
}

# 受限 scope（按资源包分别判；human allow 规则以 not is_dp_restricted_* 排除）。
is_dp_restricted_job_scope if {
	input.scope in {UPDATE_ASSIGNEE, UPDATE_STAGE}
}

is_dp_restricted_task_scope if {
	input.scope in {CREATE, DELETE, UPDATE_ASSIGNEE}
}

is_dp_restricted_project_scope if {
	input.scope in {CREATE, DELETE, UPDATE_ASSIGNEE}
}
