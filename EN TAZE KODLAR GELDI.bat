@echo off
setlocal
chcp 65001 >nul

REM =================== KULLANICI AYARLARI ===================
REM Çıktı dosya adı (aynı klasöre yazılır):
set "OUT_NAME=codepack_full.txt"

REM Parçalara ayırmak istiyorsan açık kalsın:
set "ENABLE_SPLIT=1"

REM Parça boyutu (bayt) ~ 1.8 MB:
set "CHUNK_BYTES=1800000"

REM Toplam üst sınır (bayt) ~ 5 MB:
set "MAX_TOTAL_BYTES=5000000"

REM Tek dosya üst sınırı (bayt) ~ 2 MB:
set "MAX_FILE_BYTES=2000000"
REM ==========================================================


REM Çalıştırılan klasörü ROOT ve OUT olarak al
set "ROOT=%cd%"
set "OUT=%cd%\%OUT_NAME%"

REM EXE/SCRIPT konumları (bu .bat ile aynı klasör)
set "HERE=%~dp0"
set "EXE=%HERE%codepack_v2.exe"
set "PY_SCRIPT=%HERE%codepack_v2.py"

REM Önce EXE var mı diye bak
if exist "%EXE%" (
  set "RUN_CMD="%EXE%""
) else (
  REM EXE yoksa .py var mı?
  if exist "%PY_SCRIPT%" (
    REM Python yorumlayıcısını bul (py varsa py, yoksa python)
    where py >nul 2>&1 && ( set "PY=py" ) || ( set "PY=python" )
    set "RUN_CMD=%PY% "%PY_SCRIPT%""
  ) else (
    echo HATA: codepack_v2.exe ya da codepack_v2.py bu .bat ile AYNI klasorde bulunamadi.
    echo Klasor: "%HERE%"
    pause & exit /b 1
  )
)

REM Argümanları hazırla
set "ARGS=--root "%ROOT%" --out "%OUT%" --max-total-bytes %MAX_TOTAL_BYTES% --max-file-bytes %MAX_FILE_BYTES%"

if "%ENABLE_SPLIT%"=="1" (
  set "ARGS=%ARGS% --split --chunk-bytes %CHUNK_BYTES%"
)

echo.
echo === Codepack Calisiyor ===
echo Kaynak klasor : "%ROOT%"
echo Cikti dosyasi : "%OUT%"
echo Komut        : %RUN_CMD% %ARGS%
echo.

%RUN_CMD% %ARGS%
set "ERR=%ERRORLEVEL%"

echo.
if "%ERR%"=="0" (
  echo ==== Islem bitti! ====
  echo %ROOT% klasoru paketlendi.
  echo Olusan dosya: "%OUT%"
) else (
  echo HATA! Cikis kodu: %ERR%
  echo Komut basarisiz. Yukaridaki hata mesaji dogrultusunda kontrol edin.
)

pause
endlocal
