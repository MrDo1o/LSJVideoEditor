import Foundation
import SQLite3

class KBManager {
    static let shared = KBManager()
    private var db: OpaquePointer?
    private let dbPath = "\(NSHomeDirectory())/Documents/LSJVideoProjects/kb_vault.sqlite"

    init() {
        if sqlite3_open(dbPath, &db) == SQLITE_OK {
            setupSchema()
        }
    }

    private func setupSchema() {
        let sql = """
        CREATE VIRTUAL TABLE IF NOT EXISTS vault_fts USING fts5(path, content);
        CREATE TABLE IF NOT EXISTS agent_state (
            agent_id TEXT PRIMARY KEY,
            last_active DATETIME DEFAULT CURRENT_TIMESTAMP,
            current_task TEXT,
            shared_context TEXT
        );
        """
        sqlite3_exec(db, sql, nil, nil, nil)
    }

    func search(query: String) -> [[String: String]] {
        var results: [[String: String]] = []
        var statement: OpaquePointer?
        let sql = "SELECT path, content FROM vault_fts WHERE vault_fts MATCH ? LIMIT 10"
        
        if sqlite3_prepare_v2(db, sql, -1, &statement, nil) == SQLITE_OK {
            sqlite3_bind_text(statement, 1, (query as NSString).utf8String, -1, nil)
            while sqlite3_step(statement) == SQLITE_ROW {
                let path = String(cString: sqlite3_column_text(statement, 0))
                let content = String(cString: sqlite3_column_text(statement, 1))
                results.append(["path": path, "content": content])
            }
        }
        sqlite3_finalize(statement)
        return results
    }

    func updateState(agentId: String, task: String, context: String) {
        var statement: OpaquePointer?
        let sql = "INSERT OR REPLACE INTO agent_state (agent_id, last_active, current_task, shared_context) VALUES (?, CURRENT_TIMESTAMP, ?, ?)"
        if sqlite3_prepare_v2(db, sql, -1, &statement, nil) == SQLITE_OK {
            sqlite3_bind_text(statement, 1, (agentId as NSString).utf8String, -1, nil)
            sqlite3_bind_text(statement, 2, (task as NSString).utf8String, -1, nil)
            sqlite3_bind_text(statement, 3, (context as NSString).utf8String, -1, nil)
            sqlite3_step(statement)
        }
        sqlite3_finalize(statement)
    }
}
