#pragma once
// DOKK COMMAND CENTER // MODEL SSK CLIENT (SEARCHSCOPE KAPPA)
// C++/WinRT High-Performance Client for UWP Desktop
// Protocol IOPQ-08 Locked Baseline // Zero Moderation Scanners

#include <string>
#include <vector>
#include <functional>
#include <memory>
#include <winrt/Windows.Foundation.h>
#include <winrt/Windows.Web.Http.h>

namespace LSJ::VideoElite::AI {

    struct SSKVetoResult {
        std::wstring status;            // "VERIFIED_MATCH", "VETOED", "REJECTED"
        double confidence = 0.0;
        int predicates_evaluated = 0;
        std::vector<std::wstring> vetoes_triggered;
        std::wstring primary_rejection_reason;
        double execution_duration_ms = 0.0;
        std::wstring full_thought_block;
    };

    struct SSKVisualSearchResult {
        bool match_confirmed = false;
        double confidence = 0.0;
        std::wstring perceptual_hash;
        std::wstring synthesis_report;
        std::wstring full_thought_block;
    };

    enum class SSKEventType {
        Directive,
        ReasoningToken,
        VetoEvaluation,
        VisualConsensus,
        NLEAction,
        SystemError
    };

    struct SSKLogEntry {
        std::wstring timestamp;
        SSKEventType event_type;
        std::wstring category;
        std::wstring content;
    };

    using SSKStreamCallback = std::function<void(const std::wstring& token, bool is_thought_process)>;

    class SSKClient {
    public:
        SSKClient();
        ~SSKClient();

        void Initialize(const std::wstring& base_url = L"http://127.0.0.1:8081",
                        const std::wstring& model_name = L"ssk-open-disambiguation-v1");

        // Asynchronous operations returning C++/WinRT IAsyncOperation
        winrt::Windows::Foundation::IAsyncOperation<SSKVetoResult> EvaluateVetoGateAsync(std::wstring target_entity);
        winrt::Windows::Foundation::IAsyncOperation<SSKVisualSearchResult> VisualSearchCompareAsync(
            std::wstring frame_file_path,
            std::wstring directive = L"4-1 visual search and identity compare");
        winrt::Windows::Foundation::IAsyncOperation<std::wstring> DispatchDirectiveAsync(
            std::wstring prompt,
            SSKStreamCallback stream_callback = nullptr);

        // Thought Process stream & persistence
        const std::vector<SSKLogEntry>& GetThoughtLog() const { return m_thought_log; }
        void AppendThought(const std::wstring& category, const std::wstring& content, SSKEventType type = SSKEventType::ReasoningToken);
        void ClearThoughtLog();
        std::wstring GetFormattedFullStream() const;

        bool IsOnline() const { return m_is_online; }
        const std::wstring& GetActiveModel() const { return m_model_name; }

    private:
        std::wstring m_base_url;
        std::wstring m_model_name;
        bool m_is_online = false;
        std::vector<SSKLogEntry> m_thought_log;
        winrt::Windows::Web::Http::HttpClient m_http_client{ nullptr };

        std::wstring GetCurrentTimestamp() const;
        void PersistThoughtToDisk(const SSKLogEntry& entry);
        void LoadPersistedThoughts();
    };

} // namespace LSJ::VideoElite::AI
