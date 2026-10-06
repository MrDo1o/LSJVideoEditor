// DOKK COMMAND CENTER // PROJECT SERIALIZATION IMPLEMENTATION
#include "../include/ProjectSerializer.h"
#include <fstream>
#include <sstream>

namespace LSJ::VideoElite::Storage {

    bool ProjectSerializer::SaveBinaryProject(const std::wstring& file_path, const ProjectData& project) {
        std::ofstream out(file_path, std::ios::binary);
        if (!out.is_open()) return false;

        // Magic Header "LSJB"
        const char magic[4] = { 'L', 'S', 'J', 'B' };
        out.write(magic, 4);

        int32_t version = 1;
        out.write(reinterpret_cast<const char*>(&version), sizeof(version));

        // Write basic project attributes
        int32_t name_len = static_cast<int32_t>(project.project_name.length());
        out.write(reinterpret_cast<const char*>(&name_len), sizeof(name_len));
        out.write(reinterpret_cast<const char*>(project.project_name.data()), name_len * sizeof(wchar_t));

        out.write(reinterpret_cast<const char*>(&project.width), sizeof(project.width));
        out.write(reinterpret_cast<const char*>(&project.height), sizeof(project.height));
        out.write(reinterpret_cast<const char*>(&project.fps), sizeof(project.fps));

        int32_t clip_count = static_cast<int32_t>(project.clips.size());
        out.write(reinterpret_cast<const char*>(&clip_count), sizeof(clip_count));

        for (const auto& clip : project.clips) {
            int32_t path_len = static_cast<int32_t>(clip.asset_path.length());
            out.write(reinterpret_cast<const char*>(&path_len), sizeof(path_len));
            out.write(reinterpret_cast<const char*>(clip.asset_path.data()), path_len * sizeof(wchar_t));

            out.write(reinterpret_cast<const char*>(&clip.track), sizeof(clip.track));
            out.write(reinterpret_cast<const char*>(&clip.start_seconds), sizeof(clip.start_seconds));
            out.write(reinterpret_cast<const char*>(&clip.duration_seconds), sizeof(clip.duration_seconds));
            out.write(reinterpret_cast<const char*>(&clip.source_in_seconds), sizeof(clip.source_in_seconds));
            out.write(reinterpret_cast<const char*>(&clip.speed), sizeof(clip.speed));
            out.write(reinterpret_cast<const char*>(&clip.volume), sizeof(clip.volume));
        }

        return true;
    }

    bool ProjectSerializer::LoadBinaryProject(const std::wstring& file_path, ProjectData& out_project) {
        std::ifstream in(file_path, std::ios::binary);
        if (!in.is_open()) return false;

        char magic[4];
        in.read(magic, 4);
        if (magic[0] != 'L' || magic[1] != 'S' || magic[2] != 'J' || magic[3] != 'B') {
            return false;
        }

        int32_t version = 0;
        in.read(reinterpret_cast<char*>(&version), sizeof(version));

        int32_t name_len = 0;
        in.read(reinterpret_cast<char*>(&name_len), sizeof(name_len));
        out_project.project_name.resize(name_len);
        in.read(reinterpret_cast<char*>(out_project.project_name.data()), name_len * sizeof(wchar_t));

        in.read(reinterpret_cast<char*>(&out_project.width), sizeof(out_project.width));
        in.read(reinterpret_cast<char*>(&out_project.height), sizeof(out_project.height));
        in.read(reinterpret_cast<char*>(&out_project.fps), sizeof(out_project.fps));

        int32_t clip_count = 0;
        in.read(reinterpret_cast<char*>(&clip_count), sizeof(clip_count));
        out_project.clips.clear();

        for (int32_t i = 0; i < clip_count; i++) {
            EditorClipData clip;
            int32_t path_len = 0;
            in.read(reinterpret_cast<char*>(&path_len), sizeof(path_len));
            clip.asset_path.resize(path_len);
            in.read(reinterpret_cast<char*>(clip.asset_path.data()), path_len * sizeof(wchar_t));

            in.read(reinterpret_cast<char*>(&clip.track), sizeof(clip.track));
            in.read(reinterpret_cast<char*>(&clip.start_seconds), sizeof(clip.start_seconds));
            in.read(reinterpret_cast<char*>(&clip.duration_seconds), sizeof(clip.duration_seconds));
            in.read(reinterpret_cast<char*>(&clip.source_in_seconds), sizeof(clip.source_in_seconds));
            in.read(reinterpret_cast<char*>(&clip.speed), sizeof(clip.speed));
            in.read(reinterpret_cast<char*>(&clip.volume), sizeof(clip.volume));
            out_project.clips.push_back(clip);
        }

        return true;
    }

    bool ProjectSerializer::SaveJsonProject(const std::wstring& file_path, const ProjectData& project) {
        std::wofstream out(file_path);
        if (!out.is_open()) return false;
        out << L"{\n";
        out << L"  \"version\": 1,\n";
        out << L"  \"name\": \"" << project.project_name << L"\",\n";
        out << L"  \"width\": " << project.width << L",\n";
        out << L"  \"height\": " << project.height << L",\n";
        out << L"  \"fps\": " << project.fps << L",\n";
        out << L"  \"clips\": []\n";
        out << L"}\n";
        return true;
    }

    bool ProjectSerializer::LoadJsonProject(const std::wstring& file_path, ProjectData& out_project) {
        out_project.project_name = L"Imported Project";
        return true;
    }

} // namespace LSJ::VideoElite::Storage
