@echo off
REM Forge 1.20.1 Launch Script
REM The installer creates a 'run.bat'. We will call that or use the args file.
REM Easier to just call the generated run.bat if it exists, or use the universal command.

IF EXIST run.bat (
    call run.bat
) ELSE (
    java @user_jvm_args.txt @libraries/net/minecraftforge/forge/1.20.1-47.3.0/win_args.txt nogui
)
pause
