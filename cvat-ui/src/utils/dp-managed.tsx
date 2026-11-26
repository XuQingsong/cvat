// Copyright (C) CVAT.ai Corporation
//
// SPDX-License-Identifier: MIT

// data-pipeline 托管模式（DP_PATCHES.md）：服务端 /api/server/about 下发
// dp.managed + dp.service_account；managed 且当前用户非 SA 时隐藏受限控件
// （assignee 选择器、task/project 创建入口、job stage 切换）。
// OPA rego 服务端仍是权威——这里只做 UI 收敛；about 未返回 dp 时行为同 stock。
import React from 'react';
import { useSelector } from 'react-redux';
import { CombinedState } from 'reducers';

export function useDPManagedHide(): boolean {
    return useSelector((state: CombinedState): boolean => {
        const dp = state.about.server?.dp;
        const username = state.auth.user?.username;
        return !!dp?.managed && !!username && username !== dp.serviceAccount;
    });
}

// DPManagedGate 托管模式下对非 SA 用户不渲染 children（类组件亦可包裹）。
export default function DPManagedGate(props: { children: React.ReactNode }): JSX.Element | null {
    const hide = useDPManagedHide();
    return hide ? null : <>{props.children}</>;
}
