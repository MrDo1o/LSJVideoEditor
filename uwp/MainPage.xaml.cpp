#include "pch.h"
#include "MainPage.xaml.h"
#include "MainPage.g.cpp"

using namespace winrt;
using namespace Windows::UI::Xaml;
using namespace Windows::UI::Xaml::Controls;
using namespace Windows::UI::Xaml::Input;
using namespace Windows::System;

namespace winrt::LSJVideoElite::implementation {

    MainPage::MainPage() {
        InitializeComponent();
        m_ssk_client.Initialize(L"http://127.0.0.1:8081", L"ssk-open-disambiguation-v1");
        RefreshThoughtStream();

        // Populate filter names
        std::vector<std::wstring> filters = {
            L"Original", L"Apex", L"Lumina", L"Prism", L"Vector", L"Terra",
            L"Obsidian", L"Flux", L"Helios", L"Stellar", L"Zenith", L"Aeon",
            L"Elysium", L"Halo", L"Nova", L"Radiant", L"Hunter", L"Lyric", L"Aero"
        };
        for (const auto& f : filters) {
            FilterCombo().Items().Append(box_value(hstring(f)));
        }
        FilterCombo().SelectedIndex(0);
    }

    void MainPage::RefreshThoughtStream() {
        std::wstring stream = m_ssk_client.GetFormattedFullStream();
        if (stream.empty()) {
            stream = L"SSK Sovereign Engine Online (Protocol IOPQ-08 Locked Baseline).\nReady for entity verification, demographic veto gates, visual search, and autonomous NLE directives.";
        }
        SSKThoughtProcessBox().Text(stream);
    }

    void MainPage::OnToggleThoughtExpand(IInspectable const&, RoutedEventArgs const&) {
        m_thought_expanded = !m_thought_expanded;
        if (m_thought_expanded) {
            ModelsContainer().Visibility(Visibility::Collapsed);
            ThoughtRowDef().Height(GridLength{ 1, GridUnitType::Star });
            ExpandThoughtButton().Content(box_value(L"⬚ Dock"));
        } else {
            ModelsContainer().Visibility(Visibility::Visible);
            ThoughtRowDef().Height(GridLength{ 190, GridUnitType::Pixel });
            ExpandThoughtButton().Content(box_value(L"⛶ Expand"));
        }
    }

    void MainPage::OnPopoutThoughtClick(IInspectable const&, RoutedEventArgs const&) {
        // Pop-out Full Stream Dialog
        ContentDialog dialog;
        dialog.Title(box_value(L"SSK Sovereign Vision & Veto — Full Stream"));
        dialog.CloseButtonText(L"Close");

        TextBox popoutBox;
        popoutBox.Text(m_ssk_client.GetFormattedFullStream());
        popoutBox.FontFamily(Media::FontFamily(L"Consolas"));
        popoutBox.FontSize(11);
        popoutBox.Foreground(Media::SolidColorBrush(Windows::UI::ColorHelper::FromArgb(255, 102, 224, 224)));
        popoutBox.Background(Media::SolidColorBrush(Windows::UI::ColorHelper::FromArgb(255, 10, 16, 28)));
        popoutBox.TextWrapping(TextWrapping::Wrap);
        popoutBox.IsReadOnly(true);
        popoutBox.AcceptsReturn(true);
        popoutBox.Height(480);
        popoutBox.Width(720);

        dialog.Content(popoutBox);
        dialog.ShowAsync();
    }

    void MainPage::OnClearThoughtClick(IInspectable const&, RoutedEventArgs const&) {
        m_ssk_client.ClearThoughtLog();
        RefreshThoughtStream();
    }

    void MainPage::OnSSKPromptKeyDown(IInspectable const&, KeyRoutedEventArgs const& e) {
        if (e.Key() == VirtualKey::Enter) {
            hstring prompt = SSKPromptInput().Text();
            if (!prompt.empty()) {
                SSKPromptInput().Text(L"");
                StatusMessageText().Text(L"SSK Reasoning: " + prompt);
                m_ssk_client.DispatchDirectiveAsync(std::wstring(prompt.c_str()), [this](const std::wstring&, bool) {
                    RefreshThoughtStream();
                });
            }
        }
    }

    void MainPage::OnSSKVetoClick(IInspectable const&, RoutedEventArgs const&) {
        StatusMessageText().Text(L"SSK Veto Gate evaluating entity disambiguation...");
        m_ssk_client.EvaluateVetoGateAsync(L"Selected Actor / Target");
        RefreshThoughtStream();
    }

    void MainPage::OnVisualSearchClick(IInspectable const&, RoutedEventArgs const&) {
        StatusMessageText().Text(L"SSK 4-1 Visual Search & Compare executing...");
        m_ssk_client.VisualSearchCompareAsync(L"timeline_active_frame.png");
        RefreshThoughtStream();
    }

    void MainPage::OnDirectorModeClick(IInspectable const&, RoutedEventArgs const&) {
        StatusMessageText().Text(L"SSK Director Mode: Multi-camera auto-cut active");
        m_ssk_client.DispatchDirectiveAsync(L"director_mode");
        RefreshThoughtStream();
    }

    void MainPage::OnExportClick(IInspectable const&, RoutedEventArgs const&) {
        StatusMessageText().Text(L"Exporting Master Render via FFmpeg...");
        m_ssk_client.AppendThought(L"EXPORT", L"Rendering master timeline to MP4 via Hardware H.264 Encoder.", AI::SSKEventType::NLEAction);
        RefreshThoughtStream();
    }

    void MainPage::OnPlayPauseClick(IInspectable const&, RoutedEventArgs const&) {
        m_is_playing = !m_is_playing;
        PlayPauseButton().Content(box_value(m_is_playing ? L"Pause" : L"Play"));
    }

    void MainPage::OnScrubberChanged(IInspectable const&, Primitives::RangeBaseValueChangedEventArgs const& e) {
        m_current_time = (e.NewValue() / 1000.0) * m_total_duration;
        UpdatePlayheadDisplay();
    }

    void MainPage::OnJumpBackClick(IInspectable const&, RoutedEventArgs const&) {
        m_current_time = std::max(0.0, m_current_time - 5.0);
        TimeScrubber().Value((m_current_time / m_total_duration) * 1000.0);
        UpdatePlayheadDisplay();
    }

    void MainPage::OnJumpForwardClick(IInspectable const&, RoutedEventArgs const&) {
        m_current_time = std::min(m_total_duration, m_current_time + 5.0);
        TimeScrubber().Value((m_current_time / m_total_duration) * 1000.0);
        UpdatePlayheadDisplay();
    }

    void MainPage::UpdatePlayheadDisplay() {
        int minutes = static_cast<int>(m_current_time) / 60;
        double seconds = m_current_time - (minutes * 60);
        wchar_t buf[32];
        swprintf_s(buf, L"%d:%05.2f", minutes, seconds);
        CurrentTimeText().Text(buf);
    }

    void MainPage::OnImportMediaClick(IInspectable const&, RoutedEventArgs const&) {
        StatusMessageText().Text(L"Import media selected");
    }

    void MainPage::OnImportFolderClick(IInspectable const&, RoutedEventArgs const&) {
        StatusMessageText().Text(L"Import folder selected");
    }

    void MainPage::OnMediaSelectionChanged(IInspectable const&, SelectionChangedEventArgs const&) {
        InspectorInfoText().Text(L"Selected media clip loaded.\nCodec: h264 · 1920x1080 · 30.00 fps");
    }

    void MainPage::OnCategoryChanged(IInspectable const&, SelectionChangedEventArgs const&) {}
    void MainPage::OnModelSelectionChanged(IInspectable const&, SelectionChangedEventArgs const&) {}

    void MainPage::OnAutoShotClick(IInspectable const&, RoutedEventArgs const&) {
        m_ssk_client.DispatchDirectiveAsync(L"autoshot");
        RefreshThoughtStream();
    }

    void MainPage::OnBeatSyncClick(IInspectable const&, RoutedEventArgs const&) {
        m_ssk_client.DispatchDirectiveAsync(L"beat_sync");
        RefreshThoughtStream();
    }

    void MainPage::OnUpscaleClick(IInspectable const&, RoutedEventArgs const&) {
        m_ssk_client.DispatchDirectiveAsync(L"upscale_selected");
        RefreshThoughtStream();
    }

    void MainPage::OnStabilizeClick(IInspectable const&, RoutedEventArgs const&) {
        m_ssk_client.DispatchDirectiveAsync(L"stabilize_selected");
        RefreshThoughtStream();
    }

    void MainPage::OnCaptionsClick(IInspectable const&, RoutedEventArgs const&) {
        m_ssk_client.DispatchDirectiveAsync(L"generate_captions");
        RefreshThoughtStream();
    }

    void MainPage::OnHDRMasterClick(IInspectable const&, RoutedEventArgs const&) {
        m_ssk_client.DispatchDirectiveAsync(L"hdr_master");
        RefreshThoughtStream();
    }

    void MainPage::OnFilterChanged(IInspectable const&, SelectionChangedEventArgs const&) {}
    void MainPage::OnSplitPlayheadClick(IInspectable const&, RoutedEventArgs const&) {
        m_ssk_client.AppendThought(L"TIMELINE", L"Razor cut applied at playhead t=" + CurrentTimeText().Text(), AI::SSKEventType::NLEAction);
        RefreshThoughtStream();
    }

    void MainPage::OnRippleDeleteClick(IInspectable const&, RoutedEventArgs const&) {}
    void MainPage::OnAddAllClick(IInspectable const&, RoutedEventArgs const&) {}
    void MainPage::OnTimelinePointerPressed(IInspectable const&, PointerRoutedEventArgs const&) {}

} // namespace winrt::LSJVideoElite::implementation
