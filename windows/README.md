# LSJ Elite Video Editor — Windows

Native Windows desktop editor. The Xcode/SwiftUI target is no longer required.

## Launch

Double-click `..\Launch_LSJ_Video_Editor.bat` or run:

```
python lsj_video_editor.py
```

## Stack

- Desktop shell: pywebview (WebView2)
- Preview: HTML5 video
- Probe / thumbnails / export: FFmpeg (`Gyan.FFmpeg`)
- Projects: `%USERPROFILE%\Documents\LSJProjects\*.lsj`

## Keys

| Key | Action |
| --- | --- |
| Space | Play / pause |
| S | Split at playhead |
| Delete | Remove selected |
| Ctrl+I | Import |
| Ctrl+S | Save project |
| Ctrl+E | Export |
| Ctrl+Z / Ctrl+Y | Undo / redo |
