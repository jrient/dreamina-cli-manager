[hongshu@hongshu-vostro3470 dreamina-login]$ dreamina -h
Usage:
  dreamina [flags]

即梦 official AIGC CLI tool for login, account, and generation workflows

About:
  dreamina is the 即梦 official AIGC CLI tool.

Quick start:
  1. Run "dreamina login" to save a local login session.
  2. Run a generator command such as "dreamina text2image --prompt=\"a cat portrait\"".
  3. Use "dreamina query_result --submit_id=<id>" for async tasks, or "dreamina list_task" to review saved tasks.
  4. Use "dreamina user_credit" to check the current account credit balance.

Tips:
  Run "dreamina <subcommand> -h" to view detailed help for any subcommand.
  When an AI or agent drives login, prefer "dreamina login --headless" (or "dreamina relogin --headless") over the default browser callback flow; have the user install Google Chrome (google-chrome / google-chrome-stable on Linux) first.
  When sharing the manual-import login JSON with an agent, paste the full JSON in a local terminal or send a JSON file; long pastes in chat channels are often truncated.
  All generation operations consume credits.
  Seedance 2.0 family is a flagship video generation model family and is a strong choice when output quality matters most.

Built-in Commands:
  help                 Help about any command
  import_login_response Import a copied dreamina_cli_login JSON response into the local credential store
  list_task            List saved tasks with status and result summary
  login                Log in locally before using task and account commands; use --headless for agent or remote login
  logout               Clear the local login session
  query_result         Query the current result of an async generation task
  relogin              Clear the local login session and force a fresh login; use --headless for agent or remote login
  user_credit          Show the current user's remaining credit balance
  version              Print build version and commit information


Generator Commands:
  frames2video         Submit a Dreamina first-last-frames video task
  image2image          Submit a Dreamina image-to-image task
  image2video          Animate one image into video; use multiframe2video for multi-image stories
  image_upscale        Submit a Dreamina image upscale task
  multiframe2video     Create a coherent video story from multiple images
  multimodal2video     Dreamina flagship video mode with all-around references and Seedance 2.0
  text2image           Submit a Dreamina text-to-image task
  text2video           Submit a Dreamina text-to-video task


Examples:
  dreamina login
  dreamina login --headless
  dreamina logout
  dreamina relogin
  dreamina user_credit
  dreamina list_task --gen_status=success
  dreamina query_result --submit_id=3f6eb41f425d23a3
  dreamina text2image --prompt="a cat portrait" --ratio=1:1 --resolution_type=2k


[hongshu@hongshu-vostro3470 dreamina-login]$ dreamina multimodal2video -h
Usage:
  dreamina multimodal2video [flags]

Upload local images, videos, and audio, then submit Dreamina's flagship multimodal video generation mode. This is the strongest video generation mode currently exposed in the CLI, supports all-around references, and supports the Seedance 2.0 family (flag values: seedance2.0, seedance2.0fast, seedance2.0_vip, seedance2.0fast_vip). The task is asynchronous, but --poll can wait briefly before falling back to query_result.

Supported combinations:
- inputs: any mix of --image, --video, --audio
- at least one --image or --video is required
- audio inputs must be 2-15 seconds
- model_version: seedance2.0, seedance2.0fast, seedance2.0_vip, seedance2.0fast_vip
- ratio: 1:1, 3:4, 16:9, 4:3, 9:16, 21:9
- video_resolution: 720p
- duration: 4-15s

Notes:
- local files are uploaded automatically before submit
- input limits: image<=9, video<=3, audio<=3
- 部分高内容安全风险模型在首次使用前，可能需要先在 Dreamina Web 端完成授权确认。若返回 AigcComplianceConfirmationRequired，请先完成授权后重试。


Flags:
      --image stringArray         repeat for each local input image path
      --video stringArray         repeat for each local input video path
      --audio stringArray         repeat for each local input audio path
      --prompt string             optional multimodal edit prompt
      --duration int              video duration in seconds; supported range: 4-15 (default 5)
      --ratio string              supported values: 1:1, 3:4, 16:9, 4:3, 9:16, 21:9
      --video_resolution string   supported values: 720p
      --model_version string      supported values: seedance2.0, seedance2.0fast, seedance2.0_vip, seedance2.0fast_vip
      --poll int                  submit then poll query_result for up to N seconds at 1s intervals (0 disables polling)
  -h, --help                      help for multimodal2video

Global Flags:
      --version   print build version information

Examples:
  dreamina multimodal2video --image ./input.png --prompt="turn this into a cinematic shot"
  dreamina multimodal2video --image ./input.png --audio ./music.mp3 --model_version=seedance2.0fast --duration=5
  dreamina multimodal2video --image ./input.png --video ./ref.mp4 --audio ./music.mp3 --model_version=seedance2.0fast --duration=5
