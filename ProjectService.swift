/*
 *  LSJ ELITE VIDEO EDITOR
 *  Digital Architecture by LSJ Systems TM
 *  __________________________________________________________________
 *
 *  Proprietary & Confidential. 
 *  Unauthorized copying of this file, via any medium is strictly prohibited.
 *  Architected for Professional Production & Red Team Operations.
 */

import Foundation
import AppKit

class ProjectService {
    static let shared = ProjectService()
    
    let projectsDir: URL
    
    private init() {
        let docs = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
        projectsDir = docs.appendingPathComponent("LSJProjects")
        try? FileManager.default.createDirectory(at: projectsDir, withIntermediateDirectories: true)
    }
    
    func saveProject(project: Project, gcpProjectId: String?, gcpAuthToken: String?, completion: @escaping (String) -> Void) {
        let encoder = JSONEncoder()
        guard let data = try? encoder.encode(project) else { return }
        
        let fileURL = projectsDir.appendingPathComponent("\(project.name).lsj")
        try? data.write(to: fileURL)
        
        if let gcpId = gcpProjectId, let token = gcpAuthToken {
            syncToCloud(project: project, data: data, gcpProjectId: gcpId, gcpAuthToken: token, completion: completion)
        }
    }
    
    private func syncToCloud(project: Project, data: Data, gcpProjectId: String, gcpAuthToken: String, completion: @escaping (String) -> Void) {
        let docName = project.name.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? "Untitled"
        let urlString = "https://firestore.googleapis.com/v1/projects/\(gcpProjectId)/databases/(default)/documents/projects/\(docName)"
        guard let url = URL(string: urlString) else { return }
        
        let jsonString = String(data: data, encoding: .utf8) ?? "{}"
        let payload: [String: Any] = [
            "fields": [
                "project_data": [
                    "stringValue": jsonString
                ]
            ]
        ]
        
        var request = URLRequest(url: url)
        request.httpMethod = "PATCH"
        request.setValue("Bearer \(gcpAuthToken)", forHTTPHeaderField: "Authorization")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try? JSONSerialization.data(withJSONObject: payload)
        
        Task {
            do {
                let (_, response) = try await URLSession.shared.data(for: request)
                if let httpRes = response as? HTTPURLResponse, httpRes.statusCode == 200 {
                    completion("Cloud Sync Successful")
                }
            } catch {
                print("GCP Sync failed: \(error)")
            }
        }
    }
    
    func loadRecentProjects() -> [URL] {
        let keys: [URLResourceKey] = [.contentModificationDateKey]
        guard let urls = try? FileManager.default.contentsOfDirectory(at: projectsDir, includingPropertiesForKeys: keys, options: .skipsHiddenFiles) else {
            return []
        }
        return urls.filter { $0.pathExtension == "lsj" }
            .sorted { (url1, url2) -> Bool in
                let date1 = (try? url1.resourceValues(forKeys: Set(keys)).contentModificationDate) ?? .distantPast
                let date2 = (try? url2.resourceValues(forKeys: Set(keys)).contentModificationDate) ?? .distantPast
                return date1 > date2
            }
    }
}
