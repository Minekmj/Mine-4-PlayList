#define _UNICODE
#define UNICODE

#include <windows.h>
#include <commctrl.h>
#include <dwmapi.h>
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
#pragma comment(lib, "comctl32.lib")
#pragma comment(lib, "dwmapi.lib")
#pragma comment(linker, "/subsystem:windows /entry:wWinMainCRTStartup")

// Modern Windows Common Controls (v6) 적용 매니페스트
#pragma comment(linker,"\"/manifestdependency:type='win32' \
name='Microsoft.Windows.Common-Controls' version='6.0.0.0' \
processorArchitecture='*' publicKeyToken='6595b64144ccf1df' language='*'\"")

#ifndef DWMWA_USE_IMMERSIVE_DARK_MODE
#define DWMWA_USE_IMMERSIVE_DARK_MODE 20
#endif
#ifndef DWMWA_WINDOW_CORNER_PREFERENCE
#define DWMWA_WINDOW_CORNER_PREFERENCE 33
#endif

const char *ver = "Start";
const char *repo_url = "https://github.com/Minekmj/Mine-4-PlayList/";

#define BUFFER_SIZE 8192
#define HASH_STR_LEN 65

// UI 전역 핸들 및 상태
HWND g_hWnd = NULL;
HWND g_hProgressBar = NULL;
HFONT g_hFontTitle = NULL;
HFONT g_hFontStatus = NULL;
HFONT g_hFontSub = NULL;

wchar_t g_statusText[256] = L"업데이트를 준비하는 중...";
wchar_t g_subStatusText[256] = L"잠시만 기다려주세요.";
int g_progressPercent = -1; // -1: Marquee(대기 애니메이션), 0~100: 실제 진행률
bool g_isMarquee = false;

// UI 상태 업데이트 함수
void UpdateUI(const wchar_t *status, const wchar_t *sub, int percent) {
    if (status) wcscpy(g_statusText, status);
    if (sub) wcscpy(g_subStatusText, sub);
    g_progressPercent = percent;

    if (g_hProgressBar) {
        if (percent < 0) {
            if (!g_isMarquee) {
                SetWindowLongPtr(g_hProgressBar, GWL_STYLE, WS_CHILD | WS_VISIBLE | PBS_MARQUEE);
                SendMessageW(g_hProgressBar, PBM_SETMARQUEE, TRUE, 30);
                g_isMarquee = true;
            }
        } else {
            if (g_isMarquee) {
                SendMessageW(g_hProgressBar, PBM_SETMARQUEE, FALSE, 0);
                SetWindowLongPtr(g_hProgressBar, GWL_STYLE, WS_CHILD | WS_VISIBLE | PBS_SMOOTH);
                SendMessageW(g_hProgressBar, PBM_SETRANGE32, 0, 100);
                g_isMarquee = false;
            }
            SendMessageW(g_hProgressBar, PBM_SETPOS, (WPARAM)percent, 0);
        }
    }

    if (g_hWnd) {
        InvalidateRect(g_hWnd, NULL, FALSE);
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

// 실시간 다운로드 용량 및 진행률 표시 지원
bool DownloadFile(const wchar_t *url, const wchar_t *destPath) {
    HINTERNET hInternet = InternetOpenW(L"Mozilla/5.0", INTERNET_OPEN_TYPE_PRECONFIG, NULL, NULL, 0);
    if (!hInternet) return false;

    HINTERNET hUrl = InternetOpenUrlW(hInternet, url, NULL, 0, INTERNET_FLAG_RELOAD | INTERNET_FLAG_SECURE, 0);
    if (!hUrl) {
        InternetCloseHandle(hInternet);
        return false;
    }

    // 파일 총 크기(Content-Length) 가져오기
    DWORD contentLength = 0;
    DWORD bufferSize = sizeof(contentLength);
    DWORD index = 0;
    bool hasLength = HttpQueryInfoW(hUrl, HTTP_QUERY_CONTENT_LENGTH | HTTP_QUERY_FLAG_NUMBER, &contentLength, &bufferSize, &index);

    HANDLE hFile = CreateFileW(destPath, GENERIC_WRITE, 0, NULL, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
    if (hFile == INVALID_HANDLE_VALUE) {
        InternetCloseHandle(hUrl);
        InternetCloseHandle(hInternet);
        return false;
    }

    BYTE buffer[BUFFER_SIZE];
    DWORD bytesRead = 0;
    DWORD bytesWritten = 0;
    DWORD totalDownloaded = 0;
    bool success = true;

    while (InternetReadFile(hUrl, buffer, BUFFER_SIZE, &bytesRead) && bytesRead > 0) {
        if (!WriteFile(hFile, buffer, bytesRead, &bytesWritten, NULL)) {
            success = false;
            break;
        }
        totalDownloaded += bytesRead;

        if (hasLength && contentLength > 0) {
            int percent = (int)(((double)totalDownloaded / contentLength) * 100);
            wchar_t subText[128];
            swprintf(subText, 128, L"%.1f MB / %.1f MB (%d%%)", 
                     totalDownloaded / (1024.0 * 1024.0), 
                     contentLength / (1024.0 * 1024.0), 
                     percent);
            UpdateUI(L"업데이트 패키지 다운로드 중...", subText, percent);
        } else {
            wchar_t subText[128];
            swprintf(subText, 128, L"%.1f MB 수신 중...", totalDownloaded / (1024.0 * 1024.0));
            UpdateUI(L"업데이트 패키지 다운로드 중...", subText, -1);
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

    if (!MoveFileW(currentExePath, oldExePath)) return false;
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

    UpdateUI(L"최신 버전 정보를 확인하고 있습니다...", L"GitHub 저장소 연결 중", -1);

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
        UpdateUI(L"네트워크 오류가 발생했습니다.", L"기존 프로그램을 시작합니다...", 100);
        Sleep(1200);
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
        UpdateUI(L"이미 최신 버전입니다.", L"프로그램을 실행합니다...", 100);
        Sleep(800);
        FindAndLaunchM(appDir);
        PostMessageW(g_hWnd, WM_CLOSE, 0, 0);
        return 0;
    }

    wchar_t askMsg[512];
    swprintf(askMsg, 512, L"새로운 업데이트가 발견되었습니다!\n\n현재 버전: %hs\n최신 버전: %hs\n\n지금 업데이트를 진행하시겠습니까?", currentVer, tagName);
    
    UpdateUI(L"업데이트 대기 중...", L"사용자 확인 대기 중", 0);
    if (MessageBoxW(g_hWnd, askMsg, L"업데이트 안내", MB_YESNO | MB_ICONINFORMATION) != IDYES) {
        free(json);
        UpdateUI(L"업데이트를 건너뜁니다.", L"기존 프로그램을 실행합니다...", 100);
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
        UpdateUI(L"업데이트 패키지를 찾을 수 없습니다.", L"기존 프로그램 실행 중...", 100);
        Sleep(1200);
        FindAndLaunchM(appDir);
        PostMessageW(g_hWnd, WM_CLOSE, 0, 0);
        return 1;
    }

    wchar_t downloadUrlW[1024];
    MultiByteToWideChar(CP_UTF8, 0, downloadUrlA, -1, downloadUrlW, 1024);

    wchar_t zipPath[MAX_PATH];
    swprintf(zipPath, MAX_PATH, L"%ls\\update.zip", appDir);

    UpdateUI(L"업데이트 패키지 다운로드 준비...", L"서버 요청 중...", 0);
    if (!DownloadFile(downloadUrlW, zipPath)) {
        UpdateUI(L"다운로드에 실패했습니다.", L"기존 프로그램을 실행합니다...", 100);
        Sleep(1200);
        FindAndLaunchM(appDir);
        PostMessageW(g_hWnd, WM_CLOSE, 0, 0);
        return 1;
    }

    UpdateUI(L"압축 해제 및 파일 정리 중...", L"잠시만 기다려주세요", -1);
    wchar_t tempExtractDir[MAX_PATH];
    swprintf(tempExtractDir, MAX_PATH, L"%ls\\_temp_update", appDir);

    if (!ExtractZip(zipPath, tempExtractDir)) {
        DeleteFileW(zipPath);
        UpdateUI(L"압축 해제 실패", L"기존 프로그램을 실행합니다...", 100);
        Sleep(1200);
        FindAndLaunchM(appDir);
        PostMessageW(g_hWnd, WM_CLOSE, 0, 0);
        return 1;
    }

    DeleteFileW(zipPath);

    UpdateUI(L"파일을 교체하는 중입니다...", L"실행 파일 및 구성 요소 갱신", -1);

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
            if (wcscmp(checkFd.cFileName, L".") == 0 || wcscmp(checkFd.cFileName, L"..") == 0) continue;
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
            if (wcscmp(findData.cFileName, L".") == 0 || wcscmp(findData.cFileName, L"..") == 0) continue;

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

    UpdateUI(L"업데이트 완료!", L"프로그램을 시작합니다...", 100);
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

// 윈도우 프로시저 (더블 버퍼링 & 커스텀 다크 렌더링)
LRESULT CALLBACK WndProc(HWND hWnd, UINT message, WPARAM wParam, LPARAM lParam) {
    switch (message) {
        case WM_CREATE: {
            // 다크 모드 & 둥근 모서리 활성화 (Win10/Win11)
            BOOL useDarkMode = TRUE;
            DwmSetWindowAttribute(hWnd, DWMWA_USE_IMMERSIVE_DARK_MODE, &useDarkMode, sizeof(useDarkMode));
            int cornerPref = 2; // DWMWCP_ROUND
            DwmSetWindowAttribute(hWnd, DWMWA_WINDOW_CORNER_PREFERENCE, &cornerPref, sizeof(cornerPref));

            // 세련된 Malgun Gothic 폰트 생성
            g_hFontTitle = CreateFontW(20, 0, 0, 0, FW_BOLD, FALSE, FALSE, FALSE,
                                      DEFAULT_CHARSET, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS,
                                      CLEARTYPE_QUALITY, DEFAULT_PITCH | FF_DONTCARE, L"맑은 고딕");
            g_hFontStatus = CreateFontW(15, 0, 0, 0, FW_SEMIBOLD, FALSE, FALSE, FALSE,
                                       DEFAULT_CHARSET, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS,
                                       CLEARTYPE_QUALITY, DEFAULT_PITCH | FF_DONTCARE, L"맑은 고딕");
            g_hFontSub = CreateFontW(13, 0, 0, 0, FW_NORMAL, FALSE, FALSE, FALSE,
                                    DEFAULT_CHARSET, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS,
                                    CLEARTYPE_QUALITY, DEFAULT_PITCH | FF_DONTCARE, L"맑은 고딕");

            // 프로그레스 바 생성 (초기 Marquee 모드)
            g_hProgressBar = CreateWindowExW(0, PROGRESS_CLASSW, NULL,
                                            WS_CHILD | WS_VISIBLE | PBS_MARQUEE,
                                            30, 96, 400, 10,
                                            hWnd, NULL, ((LPCREATESTRUCT)lParam)->hInstance, NULL);
            SendMessageW(g_hProgressBar, PBM_SETMARQUEE, TRUE, 30);
            g_isMarquee = true;
            break;
        }
        case WM_PAINT: {
            PAINTSTRUCT ps;
            HDC hdc = BeginPaint(hWnd, &ps);

            RECT clientRect;
            GetClientRect(hWnd, &clientRect);
            int width = clientRect.right - clientRect.left;
            int height = clientRect.bottom - clientRect.top;

            // 더블 버퍼링용 메모리 DC
            HDC memDC = CreateCompatibleDC(hdc);
            HBITMAP memBitmap = CreateCompatibleBitmap(hdc, width, height);
            HBITMAP oldBitmap = (HBITMAP)SelectObject(memDC, memBitmap);

            // 1. 다크 모드 배경 채우기 (Deep Charcoal / Zinc-900: #18181B)
            HBRUSH bgBrush = CreateSolidBrush(RGB(24, 24, 27));
            FillRect(memDC, &clientRect, bgBrush);
            DeleteObject(bgBrush);

            SetBkMode(memDC, TRANSPARENT);

            // 2. 타이틀 헤더 그리기
            SelectObject(memDC, g_hFontTitle);
            SetTextColor(memDC, RGB(250, 250, 250)); // Pure White
            RECT rcTitle = { 30, 20, width - 30, 48 };
            DrawTextW(memDC, L"Mine-4-PlayList 업데이트", -1, &rcTitle, DT_LEFT | DT_SINGLELINE | DT_NOPREFIX);

            // 3. 메인 상태 텍스트
            SelectObject(memDC, g_hFontStatus);
            SetTextColor(memDC, RGB(212, 212, 216)); // Zinc-300
            RECT rcStatus = { 30, 68, width - 30, 92 };
            DrawTextW(memDC, g_statusText, -1, &rcStatus, DT_LEFT | DT_SINGLELINE | DT_NOPREFIX);

            // 4. 서브 상태/용량 텍스트
            SelectObject(memDC, g_hFontSub);
            SetTextColor(memDC, RGB(161, 161, 170)); // Zinc-400 (Muted)
            RECT rcSub = { 30, 116, width - 30, 140 };
            DrawTextW(memDC, g_subStatusText, -1, &rcSub, DT_LEFT | DT_SINGLELINE | DT_NOPREFIX);

            // 화면으로 복사
            BitBlt(hdc, 0, 0, width, height, memDC, 0, 0, SRCCOPY);

            SelectObject(memDC, oldBitmap);
            DeleteObject(memBitmap);
            DeleteDC(memDC);

            EndPaint(hWnd, &ps);
            break;
        }
        case WM_DESTROY:
            if (g_hFontTitle) DeleteObject(g_hFontTitle);
            if (g_hFontStatus) DeleteObject(g_hFontStatus);
            if (g_hFontSub) DeleteObject(g_hFontSub);
            PostQuitMessage(0);
            break;
        default:
            return DefWindowProcW(hWnd, message, wParam, lParam);
    }
    return 0;
}

int WINAPI wWinMain(HINSTANCE hInstance, HINSTANCE hPrevInstance, PWSTR pCmdLine, int nCmdShow) {
    INITCOMMONCONTROLSEX icex;
    icex.dwSize = sizeof(INITCOMMONCONTROLSEX);
    icex.dwICC = ICC_PROGRESS_CLASS;
    InitCommonControlsEx(&icex);

    const wchar_t CLASS_NAME[] = L"ModernUpdaterWindowClass";

    WNDCLASSEXW wc = { sizeof(wc) };
    wc.lpfnWndProc = WndProc;
    wc.hInstance = hInstance;
    wc.lpszClassName = CLASS_NAME;
    wc.hbrBackground = NULL; // WM_PAINT에서 직접 그리기 위해 NULL 지정
    wc.hCursor = LoadCursor(NULL, IDC_ARROW);

    RegisterClassExW(&wc);

    // 여유롭고 균형 잡힌 창 크기 (460 x 175)
    int winWidth = 460;
    int winHeight = 175;
    int screenWidth = GetSystemMetrics(SM_CXSCREEN);
    int screenHeight = GetSystemMetrics(SM_CYSCREEN);
    int posX = (screenWidth - winWidth) / 2;
    int posY = (screenHeight - winHeight) / 2;

    g_hWnd = CreateWindowExW(WS_EX_TOPMOST, CLASS_NAME, L"Mine-4-PlayList Launcher",
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