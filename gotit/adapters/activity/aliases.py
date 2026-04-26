"""Static program alias table — maps Chinese names, abbreviations, and common
names to executable filenames for fuzzy program resolution."""

from __future__ import annotations

PROGRAM_ALIASES: dict[str, list[str]] = {
    # Windows built-in
    "记事本": ["notepad.exe"],
    "notepad": ["notepad.exe"],
    "画图": ["mspaint.exe"],
    "paint": ["mspaint.exe"],
    "计算器": ["calc.exe", "calculator.exe"],
    "calculator": ["calc.exe", "calculator.exe"],
    "资源管理器": ["explorer.exe"],
    "任务管理器": ["taskmgr.exe"],
    "命令提示符": ["cmd.exe"],
    "cmd": ["cmd.exe"],
    "终端": ["wt.exe", "cmd.exe"],
    "terminal": ["wt.exe", "cmd.exe"],
    "powershell": ["powershell.exe", "pwsh.exe"],
    "截图": ["snippingtool.exe", "snip.exe"],
    "snipping tool": ["snippingtool.exe"],
    "注册表": ["regedit.exe"],
    "控制面板": ["control.exe"],
    "远程桌面": ["mstsc.exe"],

    # Microsoft Office
    "word": ["winword.exe"],
    "excel": ["excel.exe"],
    "ppt": ["powerpnt.exe"],
    "powerpoint": ["powerpnt.exe"],
    "outlook": ["outlook.exe"],
    "onenote": ["onenote.exe"],

    # Browsers
    "浏览器": ["chrome.exe", "msedge.exe", "firefox.exe"],
    "chrome": ["chrome.exe"],
    "谷歌浏览器": ["chrome.exe"],
    "edge": ["msedge.exe"],
    "firefox": ["firefox.exe"],
    "火狐": ["firefox.exe"],

    # Dev tools
    "vscode": ["code.exe"],
    "vs code": ["code.exe"],
    "visual studio code": ["code.exe"],
    "idea": ["idea64.exe", "idea.exe"],
    "pycharm": ["pycharm64.exe", "pycharm.exe"],
    "git": ["git.exe"],

    # Creative
    "ps": ["photoshop.exe"],
    "photoshop": ["photoshop.exe"],
    "ai": ["illustrator.exe"],
    "illustrator": ["illustrator.exe"],

    # Communication
    "微信": ["wechat.exe", "weixin.exe"],
    "wechat": ["wechat.exe", "weixin.exe"],
    "qq": ["qq.exe"],
    "钉钉": ["dingtalk.exe"],
    "dingtalk": ["dingtalk.exe"],
    "teams": ["teams.exe", "ms-teams.exe"],
    "slack": ["slack.exe"],
    "飞书": ["feishu.exe", "lark.exe"],

    # Media
    "vlc": ["vlc.exe"],
    "spotify": ["spotify.exe"],
    "网易云": ["cloudmusic.exe"],
    "网易云音乐": ["cloudmusic.exe"],

    # Editors
    "notepad++": ["notepad++.exe"],
    "sublime": ["sublime_text.exe", "subl.exe"],
    "vim": ["vim.exe", "gvim.exe"],

    # Others
    "7zip": ["7zfm.exe", "7z.exe"],
    "everything": ["everything.exe"],
    "typora": ["typora.exe"],
    "postman": ["postman.exe"],
}


def resolve_aliases(name: str) -> list[str]:
    """Look up aliases for a program name. Case-insensitive."""
    key = name.strip().lower()
    if key in PROGRAM_ALIASES:
        return list(PROGRAM_ALIASES[key])

    for alias, exes in PROGRAM_ALIASES.items():
        if alias.lower() == key:
            return list(exes)

    return []
