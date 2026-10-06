#pragma once
// DOKK COMMAND CENTER // EMBEDDED FFMPEG DECODER ENGINE
// C++/WinRT High-Performance Native Video Playback
// Hardware D3D11/D3D12 Surface Mapping

#include <string>
#include <vector>
#include <memory>
#include <cstdint>
#include <winrt/Windows.Foundation.h>

namespace LSJ::VideoElite::Media {

    struct VideoStreamInfo {
        int width = 0;
        int height = 0;
        double duration_seconds = 0.0;
        double fps = 30.0;
        std::wstring codec_name;
        int64_t total_frames = 0;
        bool has_audio = false;
    };

    struct DecodedFrame {
        int width = 0;
        int height = 0;
        double timestamp_seconds = 0.0;
        std::vector<uint8_t> rgba_data;
    };

    class FFmpegDecoder {
    public:
        FFmpegDecoder();
        ~FFmpegDecoder();

        bool OpenFile(const std::wstring& file_path);
        void Close();

        const VideoStreamInfo& GetStreamInfo() const { return m_stream_info; }
        bool SeekToSeconds(double seconds);
        bool GetNextFrame(DecodedFrame& out_frame);
        bool ExtractFrameAt(double timestamp_seconds, DecodedFrame& out_frame);

        bool IsOpen() const { return m_is_open; }

    private:
        std::wstring m_current_path;
        VideoStreamInfo m_stream_info;
        bool m_is_open = false;
        double m_current_timestamp = 0.0;
        int64_t m_current_frame_index = 0;

        // Internal decoder context pointers (opaque to header)
        void* m_format_ctx = nullptr;
        void* m_codec_ctx = nullptr;
        void* m_sws_ctx = nullptr;
        int m_video_stream_index = -1;
    };

} // namespace LSJ::VideoElite::Media
