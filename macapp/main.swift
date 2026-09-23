import Cocoa
import WebKit

let dashboardURL = URL(string: "http://127.0.0.1:8768/")!
let healthURL = URL(string: "http://127.0.0.1:8768/health")!
let projectRoot = Bundle.main.object(forInfoDictionaryKey: "SLProjectRoot") as? String

final class AppDelegate: NSObject, NSApplicationDelegate, WKNavigationDelegate, WKUIDelegate {
    private var window: NSWindow!
    private var webView: WKWebView!
    private var overlay: NSVisualEffectView!
    private var statusLabel: NSTextField!
    private var spinner: NSProgressIndicator!
    private var retryButton: NSButton!
    private var hasLoaded = false

    func applicationDidFinishLaunching(_ notification: Notification) {
        buildMenu()
        buildWindow()
        NSApp.activate(ignoringOtherApps: true)
        start()
    }

    private func buildMenu() {
        let appName = "Saketh Learning"
        let mainMenu = NSMenu()

        let appItem = NSMenuItem()
        let appMenu = NSMenu()
        appMenu.addItem(withTitle: "About \(appName)", action: #selector(NSApplication.orderFrontStandardAboutPanel(_:)), keyEquivalent: "")
        appMenu.addItem(.separator())
        appMenu.addItem(withTitle: "Hide \(appName)", action: #selector(NSApplication.hide(_:)), keyEquivalent: "h")
        appMenu.addItem(withTitle: "Quit \(appName)", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        appItem.submenu = appMenu
        mainMenu.addItem(appItem)

        let editItem = NSMenuItem()
        let editMenu = NSMenu(title: "Edit")
        editMenu.addItem(withTitle: "Cut", action: #selector(NSText.cut(_:)), keyEquivalent: "x")
        editMenu.addItem(withTitle: "Copy", action: #selector(NSText.copy(_:)), keyEquivalent: "c")
        editMenu.addItem(withTitle: "Paste", action: #selector(NSText.paste(_:)), keyEquivalent: "v")
        editMenu.addItem(withTitle: "Select All", action: #selector(NSText.selectAll(_:)), keyEquivalent: "a")
        editItem.submenu = editMenu
        mainMenu.addItem(editItem)

        let viewItem = NSMenuItem()
        let viewMenu = NSMenu(title: "View")
        viewMenu.addItem(withTitle: "Reload", action: #selector(reload), keyEquivalent: "r")
        viewMenu.addItem(withTitle: "Enter Full Screen", action: #selector(NSWindow.toggleFullScreen(_:)), keyEquivalent: "f")
        viewItem.submenu = viewMenu
        mainMenu.addItem(viewItem)

        NSApp.mainMenu = mainMenu
    }

    private func buildWindow() {
        window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 1240, height: 860),
            styleMask: [.titled, .closable, .miniaturizable, .resizable],
            backing: .buffered,
            defer: false
        )
        window.title = "Saketh Learning"
        window.minSize = NSSize(width: 760, height: 580)
        window.setFrameAutosaveName("SakethLearningMain")
        window.isReleasedWhenClosed = false

        let configuration = WKWebViewConfiguration()
        webView = WKWebView(frame: .zero, configuration: configuration)
        webView.navigationDelegate = self
        webView.uiDelegate = self
        webView.autoresizingMask = [.width, .height]

        let content = NSView(frame: NSRect(x: 0, y: 0, width: 1240, height: 860))
        content.autoresizingMask = [.width, .height]
        webView.frame = content.bounds
        content.addSubview(webView)

        overlay = NSVisualEffectView(frame: content.bounds)
        overlay.autoresizingMask = [.width, .height]
        overlay.material = .windowBackground
        overlay.blendingMode = .behindWindow

        spinner = NSProgressIndicator()
        spinner.style = .spinning
        spinner.controlSize = .small
        spinner.startAnimation(nil)

        statusLabel = NSTextField(labelWithString: "Starting Saketh Learning...")
        statusLabel.alignment = .center
        statusLabel.textColor = .secondaryLabelColor
        statusLabel.font = .systemFont(ofSize: 13)

        retryButton = NSButton(title: "Try again", target: self, action: #selector(retry))
        retryButton.bezelStyle = .rounded
        retryButton.isHidden = true

        let stack = NSStackView(views: [spinner, statusLabel, retryButton])
        stack.orientation = .vertical
        stack.alignment = .centerX
        stack.spacing = 14
        stack.translatesAutoresizingMaskIntoConstraints = false
        overlay.addSubview(stack)
        NSLayoutConstraint.activate([
            stack.centerXAnchor.constraint(equalTo: overlay.centerXAnchor),
            stack.centerYAnchor.constraint(equalTo: overlay.centerYAnchor),
        ])

        content.addSubview(overlay)
        window.contentView = content
        window.center()
        window.makeKeyAndOrderFront(nil)
    }

    private func start() {
        showOverlay(message: "Starting Saketh Learning...", spinning: true, retry: false)
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            if isServerHealthy() {
                DispatchQueue.main.async { self?.loadDashboard() }
                return
            }
            startServer()
            let deadline = Date().addingTimeInterval(45)
            while Date() < deadline {
                if isServerHealthy() {
                    DispatchQueue.main.async { self?.loadDashboard() }
                    return
                }
                Thread.sleep(forTimeInterval: 0.75)
            }
            DispatchQueue.main.async {
                self?.showOverlay(
                    message: "Could not reach Saketh Learning on 127.0.0.1:8768.\nOpen Docker Desktop, then try again.",
                    spinning: false,
                    retry: true
                )
            }
        }
    }

    private func loadDashboard() {
        webView.load(URLRequest(url: dashboardURL, cachePolicy: .reloadIgnoringLocalCacheData))
    }

    private func showOverlay(message: String, spinning: Bool, retry: Bool) {
        statusLabel.stringValue = message
        spinner.isHidden = !spinning
        if spinning { spinner.startAnimation(nil) } else { spinner.stopAnimation(nil) }
        retryButton.isHidden = !retry
        overlay.isHidden = false
    }

    @objc private func retry() { start() }

    @objc private func reload() {
        if hasLoaded { webView.reload() } else { start() }
    }

    func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
        hasLoaded = true
        overlay.isHidden = true
    }

    func webView(_ webView: WKWebView, didFail navigation: WKNavigation!, withError error: Error) {
        showOverlay(message: "The learning app failed to load.\n\(error.localizedDescription)", spinning: false, retry: true)
    }

    func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!, withError error: Error) {
        showOverlay(message: "The learning app failed to load.\n\(error.localizedDescription)", spinning: false, retry: true)
    }

    func webView(_ webView: WKWebView,
                 decidePolicyFor navigationAction: WKNavigationAction,
                 decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        guard let url = navigationAction.request.url else {
            decisionHandler(.allow)
            return
        }
        if url.host == "127.0.0.1" || url.host == "localhost" || url.scheme == "about" {
            decisionHandler(.allow)
        } else {
            NSWorkspace.shared.open(url)
            decisionHandler(.cancel)
        }
    }

    func webView(_ webView: WKWebView,
                 createWebViewWith configuration: WKWebViewConfiguration,
                 for navigationAction: WKNavigationAction,
                 windowFeatures: WKWindowFeatures) -> WKWebView? {
        if let url = navigationAction.request.url { NSWorkspace.shared.open(url) }
        return nil
    }

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { true }

    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool {
        if !flag { window.makeKeyAndOrderFront(nil) }
        return true
    }
}

func isServerHealthy() -> Bool {
    var request = URLRequest(url: healthURL)
    request.timeoutInterval = 2
    request.httpMethod = "GET"
    let semaphore = DispatchSemaphore(value: 0)
    var healthy = false
    URLSession.shared.dataTask(with: request) { _, response, _ in
        if let http = response as? HTTPURLResponse, http.statusCode == 200 { healthy = true }
        semaphore.signal()
    }.resume()
    _ = semaphore.wait(timeout: .now() + 3)
    return healthy
}

func startServer() {
    guard let root = projectRoot else { return }
    let script = "\(root)/launch.sh"
    guard FileManager.default.isExecutableFile(atPath: script) else { return }

    let process = Process()
    process.executableURL = URL(fileURLWithPath: "/bin/zsh")
    process.arguments = ["-lc", "cd '\(root)' && ./launch.sh >/tmp/saketh-learning-launch.log 2>&1"]
    process.currentDirectoryURL = URL(fileURLWithPath: root)
    try? process.run()
}

let application = NSApplication.shared
let delegate = AppDelegate()
application.delegate = delegate
application.setActivationPolicy(.regular)
application.run()
