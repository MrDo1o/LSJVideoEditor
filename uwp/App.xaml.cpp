#include "pch.h"
#include "App.xaml.h"
#include "MainPage.xaml.h"

using namespace winrt;
using namespace Windows::ApplicationModel;
using namespace Windows::ApplicationModel::Activation;
using namespace Windows::UI::Xaml;
using namespace Windows::UI::Xaml::Controls;
using namespace Windows::UI::Xaml::Navigation;

namespace winrt::LSJVideoElite::implementation {
    App::App() {
        InitializeComponent();
        Suspending({ this, &App::OnSuspending });
    }

    void App::OnLaunched(LaunchActivatedEventArgs const& e) {
        Frame rootFrame{ nullptr };
        auto content = Window::Current().Content();
        if (content) {
            rootFrame = content.try_as<Frame>();
        }

        if (rootFrame == nullptr) {
            rootFrame = Frame();
            if (e.PreviousExecutionState() == ApplicationExecutionState::Terminated) {
                // Restore state if needed
            }
            Window::Current().Content(rootFrame);
        }

        if (e.PrelaunchActivated() == false) {
            if (rootFrame.Content() == nullptr) {
                rootFrame.Navigate(xaml_typename<LSJVideoElite::MainPage>(), box_value(e.Arguments()));
            }
            Window::Current().Activate();
        }
    }

    void App::OnSuspending(IInspectable const&, SuspendingEventArgs const& e) {
        auto deferral = e.SuspendingOperation().GetDeferral();
        deferral.Complete();
    }
}
