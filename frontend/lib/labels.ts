export const RISK_LEVEL_LABELS: Record<string, string> = {
  very_high: "极高",
  high: "高",
  medium: "中",
  low: "低",
  needs_review: "待核实"
};

export const RISK_LEVEL_CLASSES: Record<string, string> = {
  very_high: "bg-red-100 text-red-800 border-red-200",
  high: "bg-orange-100 text-orange-800 border-orange-200",
  medium: "bg-sky-100 text-sky-800 border-sky-200",
  low: "bg-slate-100 text-slate-700 border-slate-200",
  needs_review: "bg-amber-100 text-amber-800 border-amber-200"
};

export const SOURCE_LABELS: Record<string, string> = {
  linkedin_visible: "LinkedIn 可见页面",
  maimai_visible: "脉脉可见页面",
  arxiv: "arXiv",
  patent: "专利",
  company_site: "公司官网",
  job_site: "招聘网站",
  manual: "人工录入",
  uploaded_document: "上传文档"
};

export const REASON_CODE_LABELS: Record<string, string> = {
  profile_activity: "资料活跃",
  research_silence: "产出下降",
  team_signal: "团队信号",
  career_anniversary: "职业窗口",
  peer_movement: "同事流动",
  market_signal: "市场信号",
  manual_flag: "人工标注"
};

export const FOLLOW_STATUS_LABELS: Record<string, string> = {
  new: "新线索",
  in_pool: "已入猎场",
  watching: "观察中",
  contacted: "已触达",
  in_process: "流程中",
  closed: "已关闭"
};

export const PRIORITY_LABELS: Record<string, string> = {
  high: "高",
  medium: "中",
  low: "低"
};

export const OUTCOME_LABELS: Record<string, string> = {
  contacted: "已联系",
  no_response: "暂无回应",
  rejected: "明确拒绝",
  not_interested: "当前不感兴趣",
  interested: "表示兴趣",
  in_process: "进入流程",
  offer_sent: "已发 Offer",
  hired: "成功入职",
  bad_prediction: "AI 判断错误"
};

export const CONTACT_CHANNEL_LABELS: Record<string, string> = {
  linkedin: "LinkedIn",
  maimai: "脉脉",
  email: "邮件",
  phone: "电话",
  wechat: "微信",
  other: "其他"
};

export const BROWSER_TASK_STATUS_LABELS: Record<string, string> = {
  pending: "待执行",
  running: "执行中",
  waiting_user: "待确认",
  completed: "已完成",
  failed: "失败",
  cancelled: "已取消"
};

export const TARGET_SITE_LABELS: Record<string, string> = {
  linkedin: "LinkedIn",
  maimai: "脉脉",
  search_engine: "搜索引擎",
  arxiv: "arXiv",
  company_site: "公司官网",
  job_site: "招聘网站",
  patent: "专利"
};

export const BROWSER_TASK_TYPE_LABELS: Record<string, string> = {
  search_candidate: "搜索候选人",
  verify_profile: "验证资料",
  search_company_signal: "搜索公司信号"
};
