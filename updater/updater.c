#define _UNICODE
#define UNICODE

#include <windows.h>
#include <wininet.h>
#include <wincrypt.h>
#include <shellapi.h>
#include <shlwapi.h>
#include <stdio.h>
#include <stdbool.h>
#include <string.h>
#include <stdlib.h>

#pragma comment(lib, "user32.lib")
#pragma comment(lib, "gdi32.lib")
#pragma comment(lib, "wininet.lib")
#pragma comment(lib, "advapi32.lib")
#pragma comment(lib, "crypt32.lib")
#pragma comment(lib, "shell32.lib")
#pragma comment(lib, "shlwapi.lib")
#pragma comment(linker, "/subsystem:windows /entry:wWinMainCRTStartup")

const char *ver = "1.0.0";
const char *repo_url = "https://github.com/Minekmj/Mine-4-PlayList/";

#define BUFFER_SIZE 8192
#define HASH_STR_LEN 65

HWND g_hWnd = NULL;
HWND g_hStatusLabel = NULL;

void SetStatusText(const wchar_t *text) {
    if (g_hStatusLabel) {
        SetWindowTextW(g_hStatusLabel, text);
    }
}

bool ComputeFileSHA256(const wchar_t *filePath, char *outHashHex) {
    HANDLE hFile = CreateFileW(filePath, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING, FILE_FLAG_SEQUENTIAL_SCAN, NULL);
    if (hFile == INVALID_HANDLE_VALUE) return false;

    HCRYPTPROV hProv = 0;
    HCRYPTHASH hHash = 0;
    bool success = false;

    if (CryptAcquireContextW(&hProv, NULL, NULL, PROV_RSA_AES, CRYPT_VERIFYCONTEXT)) {
        if (CryptCreateHash(hProv, CALG_SHA_256, 0, 0, &hHash)) {
            BYTE buffer[BUFFER_SIZE];
            DWORD bytesRead = 0;

            while (ReadFile(hFile, buffer, BUFFER_SIZE, &bytesRead, NULL) && bytesRead > 0) {
                CryptHashData(hHash, buffer, bytesRead, 0);
            }

            BYTE hash[32];
            DWORD hashLen = sizeof(hash);
            if (CryptGetHashParam(hHash, HP_HASHVAL, hash, &hashLen, 0)) {
                for (int i = 0; i < 32; i++) {
                    sprintf(&outHashHex[i * 2], "%02x", hash[i]);
                }
                outHashHex[64] = '\0';
                success = true;
            }
            CryptDestroyHash(hHash);
        }
        CryptReleaseContext(hProv, 0);
    }

    CloseHandle(hFile);
    return success;
}

char* FetchAPIResponse(const wchar_t *url) {
    HINTERNET hInternet = InternetOpenW(L"Mozilla/5.0", INTERNET_OPEN_TYPE_PRECONFIG, NULL, NULL, 0);
    if (!hInternet) return NULL;

    const wchar_t *headers = L"Accept: application/vnd.github+json\r\n";
    HINTERNET hUrl = InternetOpenUrlW(hInternet, url, headers, (DWORD)-1, INTERNET_FLAG_RELOAD | INTERNET_FLAG_SECURE, 0);
    if (!hUrl) {
        InternetCloseHandle(hInternet);
        return NULL;
    }

    size_t capacity = 65536;
    size_t total = 0;
    char *buffer = (char *)malloc(capacity);
    if (!buffer) {
        InternetCloseHandle(hUrl);
        InternetCloseHandle(hInternet);
        return NULL;
    }

    DWORD bytesRead = 0;
    while (InternetReadFile(hUrl, buffer + total, (DWORD)(capacity - total - 1), &bytesRead) && bytesRead > 0) {
        total += bytesRead;
        if (capacity - total < BUFFER_SIZE) {
            capacity *= 2;
            char *newBuf = (char *)realloc(buffer, capacity);
            if (!newBuf) {
                free(buffer);
                InternetCloseHandle(hUrl);
                InternetCloseHandle(hInternet);
                return NULL;
            }
            buffer = newBuf;
        }
    }

    buffer[total] = '\0';
    InternetCloseHandle(hUrl);
    InternetCloseHandle(hInternet);
    return buffer;
}

bool DownloadFile(const wchar_t *url, const wchar_t *destPath) {
    HINTERNET hInternet = InternetOpenW(L"Mozilla/5.0", INTERNET_OPEN_TYPE_PRECONFIG, NULL, NULL, 0);
    if (!hInternet) return false;

    HINTERNET hUrl = InternetOpenUrlW(hInternet, url, NULL, 0, INTERNET_FLAG_RELOAD | INTERNET_FLAG_SECURE, 0);
    if (!hUrl) {
        InternetCloseHandle(hInternet);
        return false;
    }

    HANDLE hFile = CreateFileW(destPath, GENERIC_WRITE, 0, NULL, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
    if (hFile == INVALID_HANDLE_VALUE) {
        InternetCloseHandle(hUrl);
        InternetCloseHandle(hInternet);
        return false;
    }

    BYTE buffer[BUFFER_SIZE];
    DWORD bytesRead = 0;
    DWORD bytesWritten = 0;
    bool success = true;

    while (InternetReadFile(hUrl, buffer, BUFFER_SIZE, &bytesRead) && bytesRead > 0) {
        if (!WriteFile(hFile, buffer, bytesRead, &bytesWritten, NULL)) {
            success = false;
            break;
        }
    }

    CloseHandle(hFile);
    InternetCloseHandle(hUrl);
    InternetCloseHandle(hInternet);
    return success;
}

bool ExtractZip(const wchar_t *zipPath, const wchar_t *destDir) {
    CreateDirectoryW(destDir, NULL);

    wchar_t cmd[MAX_PATH * 3];
    swprintf(cmd, MAX_PATH * 3, L"tar.exe -xf \"%ls\" -C \"%ls\"", zipPath, destDir);

    STARTUPINFOW si = { sizeof(si) };
    PROCESS_INFORMATION pi;
    si.dwFlags = STARTF_USESHOWWINDOW;
    si.wShowWindow = SW_HIDE;

    if (!CreateProcessW(NULL, cmd, NULL, NULL, FALSE, CREATE_NO_WINDOW, NULL, NULL, &si, &pi)) {
        return false;
    }

    WaitForSingleObject(pi.hProcess, INFINITE);
    CloseHandle(pi.hProcess);
    CloseHandle(pi.hThread);
    return true;
}

bool ShellDelete(const wchar_t *path) {
    wchar_t doubleNullPath[MAX_PATH + 2] = {0};
    wcsncpy(doubleNullPath, path, MAX_PATH);

    SHFILEOPSTRUCTW fileOp = {0};
    fileOp.wFunc = FO_DELETE;
    fileOp.pFrom = doubleNullPath;
    fileOp.fFlags = FOF_NOCONFIRMATION | FOF_NOERRORUI | FOF_SILENT;
    return (SHFileOperationW(&fileOp) == 0);
}

bool ShellCopy(const wchar_t *src, const wchar_t *dst) {
    wchar_t doubleNullSrc[MAX_PATH + 2] = {0};
    wchar_t doubleNullDst[MAX_PATH + 2] = {0};
    wcsncpy(doubleNullSrc, src, MAX_PATH);
    wcsncpy(doubleNullDst, dst, MAX_PATH);

    SHFILEOPSTRUCTW fileOp = {0};
    fileOp.wFunc = FO_COPY;
    fileOp.pFrom = doubleNullSrc;
    fileOp.pTo = doubleNullDst;
    fileOp.fFlags = FOF_NOCONFIRMATION | FOF_NOCONFIRMMKDIR | FOF_NOERRORUI | FOF_SILENT;
    return (SHFileOperationW(&fileOp) == 0);
}

bool ReplaceSelf(const wchar_t *currentExePath, const wchar_t *newExePath) {
    wchar_t oldExePath[MAX_PATH];
    swprintf(oldExePath, MAX_PATH, L"%ls.old", currentExePath);

    DeleteFileW(oldExePath);

    if (!MoveFileW(currentExePath, oldExePath)) {
        return false;
    }

    if (!CopyFileW(newExePath, currentExePath, FALSE)) {
        MoveFileW(oldExePath, currentExePath);
        return false;
    }

    return true;
}

void FindAndLaunchM(const wchar_t *dir) {
    wchar_t pattern[MAX_PATH];
    swprintf(pattern, MAX_PATH, L"%ls\\M*.exe", dir);

    WIN32_FIND_DATAW fd;
    HANDLE h = FindFirstFileW(pattern, &fd);
    if (h != INVALID_HANDLE_VALUE) {
        wchar_t target[MAX_PATH];
        swprintf(target, MAX_PATH, L"%ls\\%ls", dir, fd.cFileName);
        FindClose(h);

        STARTUPINFOW si = { sizeof(si) };
        PROCESS_INFORMATION pi;
        CreateProcessW(target, NULL, NULL, NULL, FALSE, 0, NULL, dir, &si, &pi);
        CloseHandle(pi.hProcess);
        CloseHandle(pi.hThread);
    }
}

DWORD WINAPI UpdateWorkerThread(LPVOID lpParam) {
    wchar_t currentExe[MAX_PATH];
    GetModuleFileNameW(NULL, currentExe, MAX_PATH);

    wchar_t appDir[MAX_PATH];
    wcscpy(appDir, currentExe);
    PathRemoveFileSpecW(appDir);

    wchar_t oldSelfExe[MAX_PATH];
    swprintf(oldSelfExe, MAX_PATH, L"%ls.old", currentExe);
    DeleteFileW(oldSelfExe);

    SetStatusText(L"버전 정보를 확인하는 중입니다...");

    wchar_t verFilePath[MAX_PATH];
    swprintf(verFilePath, MAX_PATH, L"%ls\\ver.txt", appDir);

    char currentVer[128] = {0};
    FILE *fVer = _wfopen(verFilePath, L"r");
    if (!fVer) {
        fVer = _wfopen(verFilePath, L"w");
        if (fVer) {
            fputs(ver, fVer);
            fclose(fVer);
        }
        strncpy(currentVer, ver, sizeof(currentVer) - 1);
    } else {
        if (fgets(currentVer, sizeof(currentVer), fVer)) {
            char *end = currentVer + strlen(currentVer) - 1;
            while (end >= currentVer && (*end == '\r' || *end == '\n' || *end == ' ')) {
                *end = '\0';
                end--;
            }
        }
        fclose(fVer);
        if (strlen(currentVer) == 0) {
            strncpy(currentVer, ver, sizeof(currentVer) - 1);
        }
    }

    char owner[128] = {0};
    char repo[128] = {0};
    const char *p = strstr(repo_url, "github.com/");
    if (!p) {
        PostMessageW(g_hWnd, WM_CLOSE, 0, 0);
        return 1;
    }
    p += 11;
    sscanf(p, "%127[^/]/%127[^/]", owner, repo);

    char apiUrlA[512];
    sprintf(apiUrlA, "https://api.github.com/repos/%s/%s/releases/latest", owner, repo);

    wchar_t apiUrlW[512];
    MultiByteToWideChar(CP_UTF8, 0, apiUrlA, -1, apiUrlW, 512);

    char *json = FetchAPIResponse(apiUrlW);
    if (!json) {
        SetStatusText(L"네트워크 오류: 최신 버전을 확인할 수 없습니다.");
        Sleep(1000);
        FindAndLaunchM(appDir);
        PostMessageW(g_hWnd, WM_CLOSE, 0, 0);
        return 1;
    }

    char tagName[128] = {0};
    char *tagPos = strstr(json, "\"tag_name\":");
    if (tagPos) {
        tagPos += 11;
        while (*tagPos == ' ' || *tagPos == '\"') tagPos++;
        char *endQuote = strchr(tagPos, '\"');
        if (endQuote) {
            int len = (int)(endQuote - tagPos);
            if (len > 0 && len < 127) {
                strncpy(tagName, tagPos, len);
                tagName[len] = '\0';
            }
        }
    }

    if (strlen(tagName) == 0) {
        free(json);
        FindAndLaunchM(appDir);
        PostMessageW(g_hWnd, WM_CLOSE, 0, 0);
        return 1;
    }

    const char *cmpTag = tagName;
    if (cmpTag[0] == 'v' || cmpTag[0] == 'V') cmpTag++;
    const char *cmpVer = currentVer;
    if (cmpVer[0] == 'v' || cmpVer[0] == 'V') cmpVer++;

    if (strcmp(cmpTag, cmpVer) == 0) {
        free(json);
        SetStatusText(L"현재 최신 버전입니다. 프로그램을 시작합니다.");
        Sleep(800);
        FindAndLaunchM(appDir);
        PostMessageW(g_hWnd, WM_CLOSE, 0, 0);
        return 0;
    }

    wchar_t askMsg[512];
    swprintf(askMsg, 512, L"새로운 업데이트가 있습니다.\n\n현재 버전: %hs\n최신 버전: %hs\n\n지금 업데이트를 진행하시겠습니까?", currentVer, tagName);
    
    SetStatusText(L"업데이트 확인 대기 중...");
    if (MessageBoxW(g_hWnd, askMsg, L"업데이트 알림", MB_YESNO | MB_ICONQUESTION) != IDYES) {
        free(json);
        SetStatusText(L"업데이트를 건너뛰고 프로그램을 시작합니다.");
        Sleep(600);
        FindAndLaunchM(appDir);
        PostMessageW(g_hWnd, WM_CLOSE, 0, 0);
        return 0;
    }

    char downloadUrlA[1024] = {0};
    char *dlPos = json;
    while ((dlPos = strstr(dlPos, "\"browser_download_url\":")) != NULL) {
        dlPos += 23;
        while (*dlPos == ' ' || *dlPos == '\"') dlPos++;
        char *endQuote = strchr(dlPos, '\"');
        if (endQuote) {
            int len = (int)(endQuote - dlPos);
            if (len > 4 && _strnicmp(endQuote - 4, ".zip", 4) == 0) {
                strncpy(downloadUrlA, dlPos, len);
                downloadUrlA[len] = '\0';
                break;
            }
        }
    }

    free(json);

    if (strlen(downloadUrlA) == 0) {
        SetStatusText(L"업데이트 패키지를 찾을 수 없습니다.");
        Sleep(1000);
        FindAndLaunchM(appDir);
        PostMessageW(g_hWnd, WM_CLOSE, 0, 0);
        return 1;
    }

    wchar_t downloadUrlW[1024];
    MultiByteToWideChar(CP_UTF8, 0, downloadUrlA, -1, downloadUrlW, 1024);

    wchar_t zipPath[MAX_PATH];
    swprintf(zipPath, MAX_PATH, L"%ls\\update.zip", appDir);

    SetStatusText(L"업데이트 패키지를 다운로드하는 중입니다...");
    if (!DownloadFile(downloadUrlW, zipPath)) {
        SetStatusText(L"다운로드 실패");
        Sleep(1000);
        FindAndLaunchM(appDir);
        PostMessageW(g_hWnd, WM_CLOSE, 0, 0);
        return 1;
    }

    SetStatusText(L"압축을 해제하는 중입니다...");
    wchar_t tempExtractDir[MAX_PATH];
    swprintf(tempExtractDir, MAX_PATH, L"%ls\\_temp_update", appDir);

    if (!ExtractZip(zipPath, tempExtractDir)) {
        DeleteFileW(zipPath);
        SetStatusText(L"압축 해제 실패");
        Sleep(1000);
        FindAndLaunchM(appDir);
        PostMessageW(g_hWnd, WM_CLOSE, 0, 0);
        return 1;
    }

    DeleteFileW(zipPath);

    SetStatusText(L"파일 및 프로그램을 교체하는 중입니다...");

    wchar_t sourceRoot[MAX_PATH];
    wcscpy(sourceRoot, tempExtractDir);

    wchar_t checkPattern[MAX_PATH];
    swprintf(checkPattern, MAX_PATH, L"%ls\\*", tempExtractDir);

    WIN32_FIND_DATAW checkFd;
    HANDLE hCheck = FindFirstFileW(checkPattern, &checkFd);
    int fileCount = 0;
    int dirCount = 0;
    wchar_t singleSubDir[MAX_PATH] = {0};

    if (hCheck != INVALID_HANDLE_VALUE) {
        do {
            if (wcscmp(checkFd.cFileName, L".") == 0 || wcscmp(checkFd.cFileName, L"..") == 0) {
                continue;
            }
            if (checkFd.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) {
                dirCount++;
                wcscpy(singleSubDir, checkFd.cFileName);
            } else {
                fileCount++;
            }
        } while (FindNextFileW(hCheck, &checkFd));
        FindClose(hCheck);
    }

    if (dirCount == 1 && fileCount == 0) {
        swprintf(sourceRoot, MAX_PATH, L"%ls\\%ls", tempExtractDir, singleSubDir);
    }

    wchar_t searchPattern[MAX_PATH];
    swprintf(searchPattern, MAX_PATH, L"%ls\\*", sourceRoot);

    WIN32_FIND_DATAW findData;
    HANDLE hFind = FindFirstFileW(searchPattern, &findData);
    wchar_t launchExePath[MAX_PATH] = {0};

    if (hFind != INVALID_HANDLE_VALUE) {
        do {
            if (wcscmp(findData.cFileName, L".") == 0 || wcscmp(findData.cFileName, L"..") == 0) {
                continue;
            }

            wchar_t srcItem[MAX_PATH];
            wchar_t dstItem[MAX_PATH];
            swprintf(srcItem, MAX_PATH, L"%ls\\%ls", sourceRoot, findData.cFileName);
            swprintf(dstItem, MAX_PATH, L"%ls\\%ls", appDir, findData.cFileName);

            if (findData.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) {
                ShellDelete(dstItem);
                ShellCopy(srcItem, dstItem);
            } else {
                wchar_t *ext = PathFindExtensionW(findData.cFileName);
                if (_wcsicmp(ext, L".exe") == 0) {
                    if (findData.cFileName[0] == L'M' || findData.cFileName[0] == L'm') {
                        CopyFileW(srcItem, dstItem, FALSE);
                        wcscpy(launchExePath, dstItem);
                    } else {
                        char currentHash[HASH_STR_LEN] = {0};
                        char newHash[HASH_STR_LEN] = {0};

                        ComputeFileSHA256(currentExe, currentHash);
                        ComputeFileSHA256(srcItem, newHash);

                        if (strcmp(currentHash, newHash) != 0) {
                            ReplaceSelf(currentExe, srcItem);
                        }
                    }
                }
            }
        } while (FindNextFileW(hFind, &findData));
        FindClose(hFind);
    }

    ShellDelete(tempExtractDir);

    FILE *fUpdateVer = _wfopen(verFilePath, L"w");
    if (fUpdateVer) {
        fputs(tagName, fUpdateVer);
        fclose(fUpdateVer);
    }

    SetStatusText(L"업데이트 완료! 프로그램을 실행합니다...");
    Sleep(800);

    if (wcslen(launchExePath) > 0) {
        STARTUPINFOW si = { sizeof(si) };
        PROCESS_INFORMATION pi;
        CreateProcessW(launchExePath, NULL, NULL, NULL, FALSE, 0, NULL, appDir, &si, &pi);
        CloseHandle(pi.hProcess);
        CloseHandle(pi.hThread);
    } else {
        FindAndLaunchM(appDir);
    }

    PostMessageW(g_hWnd, WM_CLOSE, 0, 0);
    return 0;
}

LRESULT CALLBACK WndProc(HWND hWnd, UINT message, WPARAM wParam, LPARAM lParam) {
    switch (message) {
        case WM_CREATE: {
            HFONT hFont = CreateFontW(16, 0, 0, 0, FW_NORMAL, FALSE, FALSE, FALSE,
                                      DEFAULT_CHARSET, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS,
                                      CLEARTYPE_QUALITY, DEFAULT_PITCH | FF_DONTCARE, L"맑은 고딕");
            
            g_hStatusLabel = CreateWindowExW(0, L"STATIC", L"초기화 중...",
                                            WS_CHILD | WS_VISIBLE | SS_CENTER,
                                            20, 45, 380, 40,
                                            hWnd, NULL, ((LPCREATESTRUCT)lParam)->hInstance, NULL);
            SendMessageW(g_hStatusLabel, WM_SETFONT, (WPARAM)hFont, TRUE);
            break;
        }
        case WM_DESTROY:
            PostQuitMessage(0);
            break;
        default:
            return DefWindowProcW(hWnd, message, wParam, lParam);
    }
    return 0;
}

int WINAPI wWinMain(HINSTANCE hInstance, HINSTANCE hPrevInstance, PWSTR pCmdLine, int nCmdShow) {
    const wchar_t CLASS_NAME[] = L"UpdaterWindowClass";

    WNDCLASSEXW wc = { sizeof(wc) };
    wc.lpfnWndProc = WndProc;
    wc.hInstance = hInstance;
    wc.lpszClassName = CLASS_NAME;
    wc.hbrBackground = (HBRUSH)(COLOR_WINDOW + 1);
    wc.hCursor = LoadCursor(NULL, IDC_ARROW);

    RegisterClassExW(&wc);

    int winWidth = 440;
    int winHeight = 160;
    int screenWidth = GetSystemMetrics(SM_CXSCREEN);
    int screenHeight = GetSystemMetrics(SM_CYSCREEN);
    int posX = (screenWidth - winWidth) / 2;
    int posY = (screenHeight - winHeight) / 2;

    g_hWnd = CreateWindowExW(WS_EX_TOPMOST, CLASS_NAME, L"업데이터",
                             WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU | WS_MINIMIZEBOX,
                             posX, posY, winWidth, winHeight,
                             NULL, NULL, hInstance, NULL);

    if (!g_hWnd) return 0;

    ShowWindow(g_hWnd, nCmdShow);
    UpdateWindow(g_hWnd);

    HANDLE hThread = CreateThread(NULL, 0, UpdateWorkerThread, NULL, 0, NULL);
    if (hThread) CloseHandle(hThread);

    MSG msg;
    while (GetMessageW(&msg, NULL, 0, 0)) {
        TranslateMessage(&msg);
        DispatchMessageW(&msg);
    }

    return (int)msg.wParam;
}