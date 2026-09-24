#include <windows.h>
#include <filesystem>
#include <string>

namespace fs = std::filesystem;

// 静默运行命令，返回进程退出码；失败返回 -1
static int RunHidden(const std::wstring& cmd, const fs::path& workDir)
{
    STARTUPINFOW si = { sizeof(si) };
    PROCESS_INFORMATION pi = { 0 };
    si.dwFlags = STARTF_USESHOWWINDOW;
    si.wShowWindow = SW_HIDE;

    std::wstring cmdLine = cmd; // CreateProcessW 需要可写缓冲区
    if (!CreateProcessW(NULL, cmdLine.data(),
        NULL, NULL, FALSE, CREATE_NO_WINDOW, NULL,
        workDir.c_str(), &si, &pi))
    {
        return -1;
    }
    WaitForSingleObject(pi.hProcess, INFINITE);
    DWORD code = (DWORD)-1;
    GetExitCodeProcess(pi.hProcess, &code);
    CloseHandle(pi.hThread);
    CloseHandle(pi.hProcess);
    return (int)code;
}

// 读取系统代理开关状态；成功返回 true 并输出原值
static bool ReadSystemProxyEnabled(DWORD& enabled)
{
    HKEY hKey = NULL;
    if (RegOpenKeyExW(HKEY_CURRENT_USER,
            L"Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings",
            0, KEY_READ, &hKey) != ERROR_SUCCESS)
        return false;

    DWORD value = 0, size = sizeof(value), type = 0;
    LONG ret = RegQueryValueExW(hKey, L"ProxyEnable", NULL, &type,
                                reinterpret_cast<LPBYTE>(&value), &size);
    RegCloseKey(hKey);
    if (ret != ERROR_SUCCESS)
        return false;

    enabled = value;
    return true;
}

// 写入系统代理开关状态
static bool WriteSystemProxyEnabled(DWORD enabled)
{
    HKEY hKey = NULL;
    if (RegOpenKeyExW(HKEY_CURRENT_USER,
            L"Software\\Microsoft\\Windows\\CurrentVersion\\Internet Settings",
            0, KEY_SET_VALUE, &hKey) != ERROR_SUCCESS)
        return false;

    LONG ret = RegSetValueExW(hKey, L"ProxyEnable", 0, REG_DWORD,
                              reinterpret_cast<const BYTE*>(&enabled), sizeof(enabled));
    RegCloseKey(hKey);
    return ret == ERROR_SUCCESS;
}

// 临时关闭系统代理，避免 pip 走失效代理导致联网失败。
// 返回 true 表示原本代理是开启的（需要在结束后恢复）。
static bool DisableSystemProxyTemporarily()
{
    DWORD enabled = 0;
    if (!ReadSystemProxyEnabled(enabled))
        return false;
    if (enabled == 0)
        return false; // 本来就没开，无需处理

    if (WriteSystemProxyEnabled(0))
        return true; // 记录：原本是开的，需要恢复
    return false;
}

// 恢复系统代理开关
static void RestoreSystemProxy(bool wasEnabled)
{
    if (wasEnabled)
        WriteSystemProxyEnabled(1);
}

// 检查运行环境是否完整：pythonw.exe 存在 且 依赖包可正常导入
static bool IsRuntimeReady(const fs::path& appDir, const fs::path& pythonExe)
{
    if (!fs::exists(pythonExe))
        return false;

    fs::path pythonConsole = appDir / L"runtime" / L"python.exe";
    if (!fs::exists(pythonConsole))
        return false;

    // 用 python.exe 静默验证依赖包与 tkinter 是否齐全
    std::wstring checkCmd = L"\"" + pythonConsole.wstring() +
        L"\" -c \"import numpy, PIL, piexif, exifread, pywt, tkinter\"";
    return RunHidden(checkCmd, appDir) == 0;
}

int WINAPI WinMain(HINSTANCE, HINSTANCE, LPSTR, int)
{
    wchar_t szExePath[MAX_PATH] = { 0 };
    GetModuleFileNameW(NULL, szExePath, MAX_PATH);
    fs::path exePath(szExePath);
    fs::path appDir = exePath.parent_path();

    fs::path pythonExe = appDir / L"runtime" / L"pythonw.exe";
    fs::path ps1File = appDir / L"bootstrap_runtime_win7.ps1";
    fs::path mainPy = appDir / L"main.py";

    // 环境不完整时才调用 bootstrap 脚本（显示窗口）
    if (!IsRuntimeReady(appDir, pythonExe))
    {
        // 临时关闭系统代理：pip 会读取注册表代理设置，
        // 若用户开着代理但代理软件未运行，会导致下载/安装失败。
        bool proxyWasEnabled = DisableSystemProxyTemporarily();

        std::wstring cmd = L"powershell.exe -ExecutionPolicy Bypass -File \"" + ps1File.wstring() + L"\"";

        STARTUPINFOW si = { sizeof(si) };
        PROCESS_INFORMATION pi;
        si.dwFlags = STARTF_USESHOWWINDOW;
        si.wShowWindow = SW_SHOW; // 环境缺失时显示窗口，让用户看到下载进度

        if (!CreateProcessW(NULL, (LPWSTR)cmd.c_str(),
            NULL, NULL, FALSE, 0, NULL,
            appDir.c_str(), &si, &pi))
        {
            RestoreSystemProxy(proxyWasEnabled);
            MessageBoxW(NULL, L"启动下载脚本失败", L"错误", MB_ICONERROR);
            return 1;
        }
        WaitForSingleObject(pi.hProcess, INFINITE);
        CloseHandle(pi.hThread);
        CloseHandle(pi.hProcess);

        // 恢复用户原有的代理设置
        RestoreSystemProxy(proxyWasEnabled);

        // 脚本执行后再次校验环境
        if (!IsRuntimeReady(appDir, pythonExe))
        {
            MessageBoxW(NULL, L"运行环境下载失败！请检查网络", L"错误", MB_ICONERROR);
            return 1;
        }
    }

    std::wstring runCmd = L"\"" + pythonExe.wstring() + L"\" \"" + mainPy.wstring() + L"\"";
    STARTUPINFOW si2 = { sizeof(si2) };
    PROCESS_INFORMATION pi2;

    CreateProcessW(NULL, (LPWSTR)runCmd.c_str(),
        NULL, NULL, FALSE, 0, NULL,
        appDir.c_str(), &si2, &pi2);

    CloseHandle(pi2.hThread);
    CloseHandle(pi2.hProcess);

    return 0;
}
