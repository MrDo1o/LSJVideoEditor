#pragma once
#include "App.xaml.g.h"

namespace winrt::LSJVideoElite::implementation {
    struct App : AppT<App> {
        App();
        void OnLaunched(Windows::ApplicationModel::Activation::LaunchActivatedEventArgs const&);
        void OnSuspending(IInspectable const&, Windows::ApplicationModel::SuspendingEventArgs const&);
    };
}
