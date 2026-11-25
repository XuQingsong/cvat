# dp：服务账号（dp-annotation）独占 指派/生命周期/建删 的 OPA 断言。
# input 结构与 iam/permissions.py get_opa_auth_payload 一致（含 username）。
package dp_test

import rego.v1

import data.jobs
import data.tasks
import data.projects

sa := {"id": 900, "username": "dp-annotation", "privilege": "admin"}

human_admin := {"id": 1, "username": "alice", "privilege": "admin"}

human_user := {"id": 2, "username": "bob", "privilege": "user"}

job_assignee := {"id": 3, "username": "carol", "privilege": "worker"}

auth(user) := {"auth": {"user": user, "organization": null, "organization_specified": false}}

job_res := {"resource": {
	"id": 10,
	"organization": null,
	"assignee": {"id": 3},
	"task": {"id": 20, "owner": {"id": 5}, "assignee": {"id": 5},
		"project": {"id": 30, "owner": {"id": 5}, "assignee": {"id": 5}}},
}}

task_res := {"resource": {
	"id": 20,
	"organization": null, "owner": {"id": 5}, "assignee": {"id": 5},
	"project": {"id": 30, "owner": {"id": 5}, "assignee": {"id": 5}},
}}

project_res := {"resource": {"id": 30, "organization": null, "owner": {"id": 5}, "assignee": {"id": 5}}}

# --- jobs：SA 可改 assignee/stage；人类不可；worker 仍可改自己 job state ---
test_dp_sa_job_assignee if {
	jobs.allow with input as object.union_n([auth(sa), job_res, {"scope": "update:assignee"}])
}

test_dp_sa_job_stage if {
	jobs.allow with input as object.union_n([auth(sa), job_res, {"scope": "update:stage"}])
}

test_dp_human_admin_job_assignee_denied if {
	not jobs.allow with input as object.union_n([auth(human_admin), job_res, {"scope": "update:assignee"}])
}

test_dp_human_admin_job_stage_denied if {
	not jobs.allow with input as object.union_n([auth(human_admin), job_res, {"scope": "update:stage"}])
}

test_dp_worker_job_stage_denied if {
	not jobs.allow with input as object.union_n([auth(job_assignee), job_res, {"scope": "update:stage"}])
}

test_dp_worker_own_job_state_ok if {
	jobs.allow with input as object.union_n([auth(job_assignee), job_res, {"scope": "update:state"}])
}

# --- tasks：SA 可建删/指派；人类（含 admin/owner）不可 ---
test_dp_sa_task_create if {
	tasks.allow with input as object.union_n([auth(sa), task_res, {"scope": "create"}])
}

test_dp_sa_task_delete if {
	tasks.allow with input as object.union_n([auth(sa), task_res, {"scope": "delete"}])
}

test_dp_sa_task_assignee if {
	tasks.allow with input as object.union_n([auth(sa), task_res, {"scope": "update:assignee"}])
}

test_dp_human_admin_task_create_denied if {
	not tasks.allow with input as object.union_n([auth(human_admin), task_res, {"scope": "create"}])
}

test_dp_human_admin_task_delete_denied if {
	not tasks.allow with input as object.union_n([auth(human_admin), task_res, {"scope": "delete"}])
}

test_dp_human_user_task_assignee_denied if {
	not tasks.allow with input as object.union_n([auth(human_user), task_res, {"scope": "update:assignee"}])
}

# --- projects：SA 可建删/指派；人类不可 ---
test_dp_sa_project_create if {
	projects.allow with input as object.union_n([auth(sa), project_res, {"scope": "create"}])
}

test_dp_sa_project_delete if {
	projects.allow with input as object.union_n([auth(sa), project_res, {"scope": "delete"}])
}

test_dp_human_admin_project_create_denied if {
	not projects.allow with input as object.union_n([auth(human_admin), project_res, {"scope": "create"}])
}

test_dp_human_admin_project_assignee_denied if {
	not projects.allow with input as object.union_n([auth(human_admin), project_res, {"scope": "update:assignee"}])
}
