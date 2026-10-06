#pragma once
// DOKK COMMAND CENTER // PROJECT SERIALIZATION ENGINE
// Binary FlatBuffers (.lsjb) & Legacy JSON (.lsj) Bridge

#include <string>
#include <vector>
#include <memory>
#include <cstdint>

namespace LSJ::VideoElite::Storage {

    struct EditorClipData {
        std::wstring id;
        std::wstring asset_path;
        std::wstring name;
        int track = 0;
        double start_seconds = 0.0;
        double duration_seconds = 0.0;
        double source_in_seconds = 0.0;
        float speed = 1.0f;
        float volume = 1.0f;
        std::wstring filter_name = L"Original";
    };

    struct ProjectData {
        std::wstring project_name = L"Untitled Project";
        int width = 1920;
        int height = 1080;
        float fps = 30.0f;
        std::wstring active_encoder = L"Playable H.264 (Windows/Apple)";
        std::vector<EditorClipData> clips;
        std::vector<std::wstring> ssk_thoughts;
    };

    class ProjectSerializer {
    public:
        static bool SaveBinaryProject(const std::wstring& file_path, const ProjectData& project);
        static bool LoadBinaryProject(const std::wstring& file_path, ProjectData& out_project);

        static bool SaveJsonProject(const std::wstring& file_path, const ProjectData& project);
        static bool LoadJsonProject(const std::wstring& file_path, ProjectData& out_project);
    };

} // namespace LSJ::VideoElite::Storage
