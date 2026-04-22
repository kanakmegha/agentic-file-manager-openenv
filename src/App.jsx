import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { File, Folder, Check, Edit2, Play, Sparkles, LogIn, ChevronRight, ChevronDown, Network } from 'lucide-react';

// Recursive Tree Component for Proposed Architecture
const TreeView = ({ structure }) => {
  if (!structure) return null;
  const [expanded, setExpanded] = useState({});

  const toggle = (key) => setExpanded(p => ({ ...p, [key]: !p[key] }));

  return (
    <div className="pl-4 border-l border-neutral-800/50 mt-1">
      {Object.entries(structure).map(([name, node]) => {
        const isDir = node.type === 'directory';
        const isExp = expanded[name] ?? true; 
        return (
          <div key={name} className="my-1">
            <div 
              onClick={() => isDir && toggle(name)}
              className={`flex items-center gap-2 py-1 px-2 rounded-md ${isDir ? 'cursor-pointer hover:bg-neutral-800/50' : ''}`}
            >
              {isDir ? (
                isExp ? <ChevronDown className="w-3 h-3 text-neutral-500" /> : <ChevronRight className="w-3 h-3 text-neutral-500" />
              ) : <span className="w-3 h-3" />}
              {isDir ? <Folder className="w-4 h-4 text-indigo-400" /> : <File className={`w-4 h-4 ${node.staged ? 'text-emerald-400' : 'text-neutral-500 opacity-50'}`} />}
              <span className={`text-sm ${isDir ? 'text-indigo-200 font-medium' : node.staged ? 'text-emerald-200/80 font-medium' : 'text-neutral-500 italic truncate'}`}>
                {name}
              </span>
            </div>
            {isDir && isExp && node.children && <TreeView structure={node.children} />}
          </div>
        );
      })}
    </div>
  );
};

// Recursive Tree Component for Unsorted/Pending Queue
const QueueTreeView = ({ structure, activeFileName }) => {
  if (!structure) return null;
  const [expanded, setExpanded] = useState({});
  const toggle = (key) => setExpanded(p => ({ ...p, [key]: !p[key] }));

  return (
    <div className="pl-3 border-l border-neutral-800/30 mt-1">
      {Object.entries(structure).map(([name, node]) => {
        const isDir = node.type === 'directory';
        const isActive = !isDir && name === activeFileName;
        const isExp = expanded[name] ?? true;
        
        return (
          <div key={name} className="my-0.5">
            <div 
              onClick={() => isDir && toggle(name)}
              className={`flex items-center gap-2 py-1 px-2 rounded-lg text-sm transition-all ${isDir ? 'cursor-pointer hover:bg-white/5' : ''} ${isActive ? 'bg-indigo-500/10 text-indigo-300 ring-1 ring-indigo-500/20' : 'text-neutral-500'}`}
            >
              {isDir ? (
                isExp ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />
              ) : <File className={`w-3.5 h-3.5 ${isActive ? 'text-indigo-400' : 'text-neutral-600'}`} />}
              <span className={`truncate ${isDir ? 'font-medium' : ''}`}>{name}</span>
            </div>
            {isDir && isExp && node.children && <QueueTreeView structure={node.children} activeFileName={activeFileName} />}
          </div>
        );
      })}
    </div>
  );
};

// Summary component for the changeset
const ChangesetView = ({ log }) => (
  <div className="w-full max-w-3xl bg-neutral-900/50 border border-neutral-800 rounded-2xl overflow-hidden shadow-2xl">
    <div className="p-6 border-b border-neutral-800 bg-neutral-900/50 flex items-center justify-between">
      <h3 className="text-sm font-semibold tracking-wider text-neutral-400 uppercase">Deployment Changeset</h3>
      <div className="flex gap-2">
        <span className="px-3 py-1 bg-emerald-500/10 text-emerald-400 text-xs font-bold rounded-full border border-emerald-500/20">
          {log.filter(l => l.status === 'success' && !l.note).length} MOVED
        </span>
        <span className="px-3 py-1 bg-neutral-500/10 text-neutral-400 text-xs font-bold rounded-full border border-neutral-800">
          {log.filter(l => l.note === 'Existing').length} UNCHANGED
        </span>
      </div>
    </div>
    <div className="max-h-[400px] overflow-y-auto p-4 flex flex-col gap-3">
      {log.map((item, idx) => {
        const isStatic = item.note === 'Existing';
        return (
          <div key={idx} className={`flex flex-col gap-2 p-3 border rounded-xl group transition-colors ${isStatic ? 'bg-neutral-950/20 border-neutral-800/30 opacity-60' : 'bg-neutral-950/50 border-neutral-800/50 hover:border-neutral-700'}`}>
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-white truncate max-w-[200px]">{item.name}</span>
              {item.status === 'success' ? (
                isStatic ? (
                  <div className="text-neutral-500 text-[10px] font-bold uppercase tracking-tighter">No Change Required</div>
                ) : (
                  <div className="flex items-center gap-1 text-emerald-400 text-[10px] font-bold uppercase tracking-tighter">
                    <Check className="w-3 h-3" /> Moved
                  </div>
                )
              ) : (
                <div className="text-rose-500 text-[10px] font-bold uppercase tracking-tighter">Failed</div>
              )}
            </div>
            <div className="flex items-center gap-2 text-[10px] font-mono text-neutral-500 overflow-hidden">
              <span className="truncate flex-1 text-neutral-600 italic">{item.from}</span>
              <ChevronRight className="w-3 h-3 flex-shrink-0" />
              <span className={`truncate flex-1 ${isStatic ? 'text-neutral-500' : 'text-indigo-300'}`}>{item.to}</span>
            </div>
            {item.error && <p className="text-[10px] text-rose-400 italic">Error: {item.error}</p>}
          </div>
        );
      })}
    </div>
  </div>
);

export default function App() {
  const [directoryHandle, setDirectoryHandle] = useState(null);
  const [unsortedFiles, setUnsortedFiles] = useState([]); // array of file objects
  const [analyzedStructure, setAnalyzedStructure] = useState({}); // { fileName: { path, reason } }
  const [currentIndex, setCurrentIndex] = useState(0);
  const [stagedState, setStagedState] = useState({}); // { fileName: { fileObj, path, reason } }
  
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState("");
  
  const [isFinished, setIsFinished] = useState(false);
  const [organizing, setOrganizing] = useState(false);
  const [success, setSuccess] = useState(false);
  const [loadingMsg, setLoadingMsg] = useState("");
  const [executionLog, setExecutionLog] = useState([]);

  const getFilesRecursively = async (dirHandle, relPath = '') => {
    let files = [];
    for await (const entry of dirHandle.values()) {
      if (entry.kind === 'file') {
        const fullRelPath = relPath ? `${relPath}/${entry.name}` : entry.name;
        files.push({ 
          handle: entry, 
          parentHandle: dirHandle,
          relative_path: fullRelPath,
          name: entry.name 
        });
      } else if (entry.kind === 'directory') {
        const nextRelPath = relPath ? `${relPath}/${entry.name}` : entry.name;
        const subFiles = await getFilesRecursively(entry, nextRelPath);
        files = files.concat(subFiles);
      }
    }
    return files;
  };

  const handleSelectFolder = async () => {
    try {
      const dirHandle = await window.showDirectoryPicker({ mode: 'read' });
      setDirectoryHandle(dirHandle);
      
      const fileEntries = await getFilesRecursively(dirHandle);
      setUnsortedFiles(fileEntries);
      
      if (fileEntries.length > 0) {
        setLoadingMsg("Analyzing entire structure...");
        const payload = fileEntries.map(f => ({ name: f.name, relative_path: f.relative_path }));
        await fetchStructureAnalysis(payload);
        setLoadingMsg("");
      } else {
        setIsFinished(true);
      }
    } catch (e) {
      console.error(e);
      if (e.name !== 'AbortError') {
         alert("Failed to access directory. Ensure you use a Chromium-based browser.");
      }
      setLoadingMsg("");
    }
  };

  const fetchStructureAnalysis = async (fileNames) => {
    try {
      const res = await fetch('/api/analyze-structure', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ files: fileNames })
      });
      if (!res.ok) {
        console.error("Server returned status:", res.status);
        const text = await res.text();
        console.error("Response body:", text);
        setAnalyzedStructure({});
        return;
      }
      
      const textResponse = await res.text();
      if (!textResponse) {
         console.warn("Empty response from server");
         setAnalyzedStructure({});
         return;
      }
      
      try {
         const data = JSON.parse(textResponse);
         setAnalyzedStructure(data.structure || {});
      } catch (e) {
         console.error("JSON parse error:", e, "Payload:", textResponse.substring(0, 200));
         setAnalyzedStructure({});
      }
    } catch (e) {
      console.error("Fetch error:", e);
    }
  };

  const reEvaluateStructure = async (remainingNames, overrideName, overridePath) => {
    try {
      setLoadingMsg("Re-evaluating based on your pattern...");
      const res = await fetch('/api/reevaluate-structure', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
           remaining_files: remainingNames,
           override_file: overrideName,
           override_path: overridePath
        })
      });
      
      const textResponse = await res.text();
      if (!res.ok || !textResponse) {
         setLoadingMsg("");
         return;
      }
      
      const data = JSON.parse(textResponse);
      
      // Merge new intelligence into existing state without touching already staged
      setAnalyzedStructure(prev => ({
        ...prev,
        ...data.structure
      }));
      setLoadingMsg("");
    } catch (e) {
      console.error(e);
      setLoadingMsg("");
    }
  };

  const nextFile = async (customPath = null) => {
    const currentFileObj = unsortedFiles[currentIndex];
    const dataObj = analyzedStructure[currentFileObj.name] || { path: "Uncategorized", reason: "Fallback" };
    const finalPath = customPath || dataObj.path;
    
    setStagedState(prev => ({ 
      ...prev, 
      [currentFileObj.name]: { 
        fileObj: currentFileObj, 
        path: finalPath,
        reason: customPath ? "User Defined override" : dataObj.reason
      } 
    }));
    
    const isOverride = customPath && customPath !== dataObj.path;
    const remainingFiles = unsortedFiles.slice(currentIndex + 1).map(f => f.name);
    
    if (isOverride && remainingFiles.length > 0) {
       await reEvaluateStructure(remainingFiles, currentFileObj.name, finalPath);
    }

    if (currentIndex + 1 < unsortedFiles.length) {
      setCurrentIndex(currentIndex + 1);
      setIsEditing(false);
    } else {
      setIsFinished(true);
    }
  };

  const approveAllRemaining = () => {
    const remaining = unsortedFiles.slice(currentIndex);
    const newStaged = { ...stagedState };
    
    remaining.forEach(fileObj => {
      const dataObj = analyzedStructure[fileObj.name] || { path: "Uncategorized", reason: "Fallback" };
      newStaged[fileObj.name] = {
        fileObj: fileObj,
        path: dataObj.path,
        reason: dataObj.reason
      };
    });
    
    setStagedState(newStaged);
    setCurrentIndex(unsortedFiles.length);
    setIsFinished(true);
  };

  const buildTree = (stagedObj, projectedObj = {}) => {
    const root = {};
    const mergeIntoTree = (obj, isStaged) => {
      for (const [fileName, val] of Object.entries(obj)) {
        if (!val.path) continue;
        const parts = val.path.split('/').filter(Boolean);
        let curr = root;
        parts.forEach(p => {
          if (!curr[p]) curr[p] = { type: 'directory', children: {} };
          curr = curr[p].children;
        });
        curr[fileName] = { type: 'file', staged: isStaged };
      }
    };

    mergeIntoTree(projectedObj, false);
    mergeIntoTree(stagedObj, true);
    return root;
  };

  const executeOrganization = async () => {
    if (!directoryHandle) return;
    try {
      setOrganizing(true);
      
      if ((await directoryHandle.queryPermission({ mode: 'readwrite' })) !== 'granted') {
        const permissionStatus = await directoryHandle.requestPermission({ mode: 'readwrite' });
        if (permissionStatus !== 'granted') {
          alert("Write permission is required to actually move the files.");
          setOrganizing(false);
          return;
        }
      }
      
      const log = [];
      for (const [fileName, stageData] of Object.entries(stagedState)) {
        const { fileObj, path } = stageData;
        const targetPath = path.replace(/^\//, '').replace(/\/$/, '');
        const currentPath = fileObj.relative_path;
        const targetFull = targetPath + "/" + fileName;

        try {
          if (targetPath === fileObj.parentHandle.name || (targetPath === "" && fileObj.parentHandle === directoryHandle)) {
             log.push({ name: fileName, from: currentPath, to: targetFull, status: 'success', note: 'Existing' });
             continue;
          }

          const parts = targetPath.split('/').filter(Boolean);
          let targetFolderHandle = directoryHandle;
          for (const part of parts) {
             targetFolderHandle = await targetFolderHandle.getDirectoryHandle(part, { create: true });
          }
          
          const fileData = await fileObj.handle.getFile();
          const writableFileHandle = await targetFolderHandle.getFileHandle(fileName, { create: true });
          const writableStream = await writableFileHandle.createWritable();
          await writableStream.write(fileData);
          await writableStream.close();
          
          await fileObj.parentHandle.removeEntry(fileName);
          log.push({ name: fileName, from: currentPath, to: targetFull, status: 'success' });
        } catch (e) {
          console.error(e);
          log.push({ name: fileName, from: currentPath, to: targetFull, status: 'error', error: e.message });
        }
      }

      setExecutionLog(log);
      setSuccess(true);
    } catch (e) {
      console.error(e);
      alert("Failed to organize files. Check console for details.");
    } finally {
      setOrganizing(false);
    }
  };

  if (!directoryHandle) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-neutral-950 text-neutral-50 font-sans">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="text-center">
           <Folder className="w-16 h-16 text-indigo-500 mx-auto mb-6" />
           <h1 className="text-4xl font-semibold mb-4 tracking-tight">Semantic File Organizer</h1>
           <p className="text-neutral-400 max-w-lg mx-auto mb-10">
             Grant access to a local folder to systematically analyze and design a Normalized Folder Hierarchy.
           </p>
           <button 
             onClick={handleSelectFolder}
             className="py-4 px-8 rounded-xl font-medium text-white bg-indigo-600 hover:bg-indigo-500 transition-all flex items-center gap-3 mx-auto shadow-lg shadow-indigo-500/20"
           >
             <LogIn className="w-5 h-5" /> Select Folder
           </button>
        </motion.div>
      </div>
    );
  }

  const currentFileObj = unsortedFiles[currentIndex];
  const currentStructureData = currentFileObj && analyzedStructure[currentFileObj.name] 
          ? analyzedStructure[currentFileObj.name] 
          : { path: "Evaluating...", reason: "..." };

  return (
    <div className="flex h-screen w-full bg-neutral-950 text-neutral-50 font-sans overflow-hidden">
      {/* Sidebar Tree View */}
      <div className="w-96 border-r border-neutral-800 bg-neutral-900/30 flex flex-col p-6 overflow-y-auto">
        <div className="flex items-center gap-2 mb-8 text-neutral-300">
          <Network className="w-5 h-5" />
          <h1 className="text-lg font-medium tracking-tight">Structured Pipeline</h1>
        </div>
        
        <div className="mb-6">
          <h2 className="text-xs uppercase tracking-wider text-indigo-500 font-semibold mb-3">Proposed Architecture</h2>
          <div className="bg-neutral-950/50 rounded-xl p-3 border border-neutral-800/50 min-h-[100px]">
             {Object.keys(analyzedStructure).length === 0 ? (
               <p className="text-sm text-neutral-500 italic text-center mt-3">Analyzing structure...</p>
             ) : (
               <TreeView structure={buildTree(stagedState, analyzedStructure)} />
             )}
          </div>
        </div>

        <h2 className="text-xs uppercase tracking-wider text-neutral-500 font-semibold mb-3">Pending Queue</h2>
        <div className="overflow-y-auto max-h-[400px] -mx-2 px-2 scrollbar-hide">
          {(() => {
            const remainingFiles = unsortedFiles.slice(currentIndex);
            if (remainingFiles.length === 0) return <span className="text-sm text-neutral-600 px-3 py-2 italic">Queue Empty</span>;
            
            // Build tree representation of the remaining files
            const queueTree = {};
            remainingFiles.forEach(f => {
              const parts = f.relative_path.split('/').filter(Boolean);
              let curr = queueTree;
              parts.forEach((p, i) => {
                const isFile = i === parts.length - 1;
                if (!curr[p]) {
                  curr[p] = isFile ? { type: 'file' } : { type: 'directory', children: {} };
                }
                curr = isFile ? curr[p] : curr[p].children;
              });
            });

            return <QueueTreeView structure={queueTree} activeFileName={currentFileObj?.name} />;
          })()}
        </div>
      </div>

      {/* Main Stage */}
      <div className="flex-1 flex flex-col items-center justify-center p-8 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-neutral-900 via-neutral-950 to-neutral-950 relative">
        {loadingMsg && (
           <div className="absolute top-10 flex items-center gap-3 px-4 py-2 bg-indigo-500/10 border border-indigo-500/20 rounded-full animate-pulse text-indigo-300 text-sm font-medium shadow-lg shadow-indigo-500/10">
              <Sparkles className="w-4 h-4" /> {loadingMsg}
           </div>
        )}

        <AnimatePresence mode="wait">
          {!isFinished && currentFileObj ? (
            <motion.div
              key={currentFileObj.path}
              initial={{ opacity: 0, y: 20, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, x: -50, scale: 0.95 }}
              transition={{ duration: 0.4, ease: [0.23, 1, 0.32, 1] }}
              className="w-full max-w-2xl"
            >
              <div className="bg-neutral-900/50 border border-neutral-800 backdrop-blur-xl rounded-2xl p-8 shadow-2xl">
                <div className="flex items-center justify-between mb-8">
                  <div className="flex items-center gap-2 text-neutral-400">
                    <File className="w-5 h-5 text-indigo-400" />
                    <span className="text-sm font-medium tracking-wide">Structural Architect</span>
                  </div>
                  <div className="flex items-center gap-1.5 px-3 py-1 bg-amber-500/10 border border-amber-500/20 rounded-full">
                    <span className="text-xs font-semibold tracking-wide text-amber-500 max-w-[200px] truncate" title={currentStructureData.reason}>
                       {currentStructureData.reason || "Normalization"}
                    </span>
                  </div>
                </div>

                <div className="mb-10 text-center">
                  <h2 className="text-3xl font-semibold tracking-tight text-white mb-2 line-clamp-1">{currentFileObj.name}</h2>
                  <p className="text-xs text-neutral-500 font-mono tracking-wider">{currentFileObj.relative_path}</p>
                </div>

                <div className="bg-neutral-950/50 rounded-xl p-6 mb-8 border border-neutral-800/50 text-center relative overflow-hidden group">
                  <p className="text-sm text-neutral-500 mb-2 font-medium">Proposed Full Path</p>
                  
                  {isEditing ? (
                    <input 
                      autoFocus
                      type="text"
                      value={editValue}
                      onChange={e => setEditValue(e.target.value)}
                      placeholder="/Parent/Child"
                      className="bg-neutral-900 border border-indigo-500 rounded-md text-indigo-300 text-lg font-mono outline-none text-center w-full px-4 py-2"
                    />
                  ) : (
                    <div className="flex flex-col items-center">
                      <p className="text-xl text-indigo-300 font-mono tracking-tight bg-neutral-900/50 py-2 px-4 rounded-md inline-block">
                        {currentStructureData.path}
                      </p>
                      <span className="text-[10px] text-neutral-600 mt-2 font-mono">/ {currentFileObj.name}</span>
                    </div>
                  )}
                </div>

                <div className="flex gap-4">
                  {isEditing ? (
                    <>
                      <button 
                        onClick={() => setIsEditing(false)}
                        className="flex-1 py-3 px-6 rounded-xl font-medium text-neutral-300 border border-neutral-700 hover:bg-neutral-800 transition-colors"
                      >
                        Cancel
                      </button>
                      <button 
                        onClick={() => nextFile(editValue.replace(/^\//,'').trim() || "Uncategorized")}
                        className="flex-1 py-3 px-6 rounded-xl font-medium text-white bg-indigo-600 hover:bg-indigo-500 transition-colors"
                      >
                        Learn & Apply
                      </button>
                    </>
                  ) : (
                    <>
                      <button 
                        onClick={() => {
                          setEditValue("/" + currentStructureData.path);
                          setIsEditing(true);
                        }}
                        className="flex-1 py-3 px-6 rounded-xl font-medium text-white bg-neutral-800 border border-neutral-700 hover:bg-neutral-700 transition-colors flex items-center justify-center gap-2"
                      >
                        <Edit2 className="w-4 h-4" /> Override Path
                      </button>
                      <button 
                         onClick={() => nextFile()}
                         disabled={loadingMsg !== ""}
                         className="flex-1 py-3 px-6 rounded-xl font-medium text-emerald-950 bg-emerald-500 hover:bg-emerald-400 transition-colors flex items-center justify-center shadow-[0_0_20px_rgba(16,185,129,0.3)] hover:shadow-[0_0_30px_rgba(16,185,129,0.5)] disabled:opacity-50"
                       >
                         Approve Structure
                       </button>
                    </>
                  )}
                </div>
                {!isEditing && (
                  <button 
                    onClick={approveAllRemaining}
                    className="w-full mt-4 py-2 text-xs uppercase tracking-widest font-bold text-neutral-500 hover:text-indigo-400 transition-colors border border-dashed border-neutral-800 hover:border-indigo-500/50 rounded-lg"
                  >
                    Approve All Remaining
                  </button>
                )}
              </div>
            </motion.div>
          ) : success ? (
            <motion.div
              key="success"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="w-full flex flex-col items-center"
            >
              <div className="w-16 h-16 bg-emerald-500/20 rounded-full flex items-center justify-center mb-6">
                <Check className="w-8 h-8 text-emerald-400" />
              </div>
              <h2 className="text-3xl font-semibold mb-2 text-white">Hierarchy Deployed</h2>
              <p className="text-neutral-400 max-w-md mx-auto mb-10 text-center text-sm">
                The architecture has been successfully written to your disk. Review the changeset below.
              </p>
              
              <ChangesetView log={executionLog} />
              
              <button 
                 onClick={() => window.location.reload()}
                 className="mt-8 py-3 px-8 rounded-xl font-medium text-neutral-400 hover:text-white transition-colors bg-neutral-900 border border-neutral-800 hover:border-neutral-700"
              >
                Close & Restart
              </button>
            </motion.div>
          ) : (
            <motion.div
              key="final"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="w-full max-w-2xl bg-neutral-900/50 border border-neutral-800 backdrop-blur-xl rounded-2xl p-10 shadow-2xl text-center"
            >
              <Sparkles className="w-12 h-12 text-indigo-500 mx-auto mb-6" />
              <h2 className="text-3xl font-semibold mb-4 text-white">Staging Complete</h2>
              <p className="text-neutral-400 mb-8 max-w-md mx-auto">
                The folder hierarchy architecture is finalized. Execute to run the deployment on your disk.
              </p>
              
              <button 
                onClick={executeOrganization}
                disabled={organizing}
                className="w-full py-4 px-6 rounded-xl font-medium text-emerald-950 bg-emerald-500 hover:bg-emerald-400 transition-all flex items-center justify-center gap-2 text-lg shadow-[0_0_20px_rgba(16,185,129,0.3)] disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {organizing ? "Deploying Architecture..." : (
                  <>
                    <Play className="w-5 h-5 fill-current" /> Execute Organization
                  </>
                )}
              </button>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
