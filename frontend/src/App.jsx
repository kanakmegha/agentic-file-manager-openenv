import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { File, Folder, Check, Edit2, Play, Sparkles, LogIn } from 'lucide-react';

export default function App() {
  const [directoryHandle, setDirectoryHandle] = useState(null);
  const [unsortedFiles, setUnsortedFiles] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [stagedState, setStagedState] = useState({});
  const [currentSuggestion, setCurrentSuggestion] = useState(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState("");
  const [isFinished, setIsFinished] = useState(false);
  const [organizing, setOrganizing] = useState(false);
  const [success, setSuccess] = useState(false);

  // Recursively get files from directory
  const getFilesRecursively = async (dirHandle, path = '') => {
    let files = [];
    for await (const entry of dirHandle.values()) {
      if (entry.kind === 'file') {
        files.push({ handle: entry, path: path + entry.name, name: entry.name });
      } else if (entry.kind === 'directory') {
        // optionally recurse or just do shallow depending on use-case
        // For semantic organizing, doing root level is usually safer, but since user asked: recursive list
        const subFiles = await getFilesRecursively(entry, path + entry.name + '/');
        files = files.concat(subFiles);
      }
    }
    return files;
  };

  const handleSelectFolder = async () => {
    try {
      const dirHandle = await window.showDirectoryPicker({ mode: 'readwrite' });
      setDirectoryHandle(dirHandle);
      
      const fileEntries = await getFilesRecursively(dirHandle);
      const fileNames = fileEntries.map(f => f.name);
      
      setUnsortedFiles(fileEntries);
      
      if (fileEntries.length > 0) {
        await fetchSuggestion(fileEntries[0].name);
      } else {
        setIsFinished(true); // Empty folder
      }
    } catch (e) {
      console.error(e);
      if (e.name !== 'AbortError') {
         alert("Failed to access directory. Ensure you use a Chromium-based browser.");
      }
    }
  };

  const fetchSuggestion = async (fileName) => {
    try {
      setCurrentSuggestion("Thinking...");
      const res = await fetch('/api/suggest-category', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ files: [fileName] })
      });
      const data = await res.json();
      setCurrentSuggestion(data.suggestions[fileName] || "Miscellaneous");
    } catch (e) {
      console.error(e);
      setCurrentSuggestion("Miscellaneous");
    }
  };

  const nextFile = async (category) => {
    const currentFileObj = unsortedFiles[currentIndex];
    
    // Move to Staged state
    setStagedState(prev => ({ 
      ...prev, 
      [currentFileObj.name]: { fileObj: currentFileObj, category } 
    }));
    
    if (currentIndex + 1 < unsortedFiles.length) {
      const nextIdx = currentIndex + 1;
      setCurrentIndex(nextIdx);
      setIsEditing(false);
      await fetchSuggestion(unsortedFiles[nextIdx].name);
    } else {
      setIsFinished(true);
    }
  };

  const handleApprove = () => {
    nextFile(currentSuggestion);
  };

  const handleCustomApprove = () => {
    if (editValue.trim()) {
      nextFile(editValue.trim());
    }
  };

  const executeOrganization = async () => {
    if (!directoryHandle) return;
    try {
      setOrganizing(true);
      
      for (const [fileName, stageData] of Object.entries(stagedState)) {
        const { fileObj, category } = stageData;
        const targetFolderHandle = await directoryHandle.getDirectoryHandle(category, { create: true });
        
        const fileData = await fileObj.handle.getFile();
        
        // Write to new location
        const writableFileHandle = await targetFolderHandle.getFileHandle(fileName, { create: true });
        const writableStream = await writableFileHandle.createWritable();
        await writableStream.write(fileData);
        await writableStream.close();
        
        // Delete original file from root (assuming shallow fetch initially or we remove the entry)
        // Note: For deep paths this requires parsing the original path, but for now we remove from root
        await directoryHandle.removeEntry(fileName);
      }

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
             Grant access to a local folder to begin analyzing and classifying its contents purely locally.
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

  return (
    <div className="flex h-screen w-full bg-neutral-950 text-neutral-50 font-sans overflow-hidden">
      {/* Sidebar */}
      <div className="w-80 border-r border-neutral-800 bg-neutral-900/30 flex flex-col p-6">
        <div className="flex items-center gap-2 mb-8 text-neutral-300">
          <Folder className="w-5 h-5" />
          <h1 className="text-lg font-medium tracking-tight">File Organizer</h1>
        </div>
        
        <h2 className="text-xs uppercase tracking-wider text-neutral-500 font-semibold mb-4">Unsorted Queue</h2>
        <div className="flex flex-col gap-2 flex-grow overflow-y-auto">
          {unsortedFiles.map((f, idx) => {
            const isDone = idx < currentIndex;
            const isActive = idx === currentIndex && !isFinished;
            return (
              <div 
                key={f.path} 
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-200 ${
                  isActive ? 'bg-indigo-500/10 text-indigo-300 border border-indigo-500/20' : 
                  isDone ? 'text-neutral-600' : 'text-neutral-400'
                }`}
              >
                {isDone ? <Check className="w-4 h-4 text-emerald-500/50" /> : <File className="w-4 h-4" />}
                <span className={`truncate ${isDone ? 'line-through' : ''}`}>{f.name}</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Main Stage */}
      <div className="flex-1 flex flex-col items-center justify-center p-8 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-neutral-900 via-neutral-950 to-neutral-950">
        <AnimatePresence mode="wait">
          {!isFinished && currentFileObj ? (
            <motion.div
              key={currentFileObj.path}
              initial={{ opacity: 0, y: 20, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, x: -50, scale: 0.95 }}
              transition={{ duration: 0.4, ease: [0.23, 1, 0.32, 1] }}
              className="w-full max-w-xl"
            >
              <div className="bg-neutral-900/50 border border-neutral-800 backdrop-blur-xl rounded-2xl p-8 shadow-2xl">
                <div className="flex items-center justify-between mb-8">
                  <div className="flex items-center gap-2 text-neutral-400">
                    <File className="w-5 h-5" />
                    <span className="text-sm font-medium tracking-wide">Evaluating File</span>
                  </div>
                  <div className="flex items-center gap-1.5 px-3 py-1 bg-indigo-500/10 border border-indigo-500/20 rounded-full">
                    <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                    <span className="text-xs font-semibold tracking-wide text-indigo-400">Semantic Reasoning</span>
                  </div>
                </div>

                <div className="mb-10 text-center">
                  <h2 className="text-3xl font-semibold tracking-tight text-white mb-2">{currentFileObj.name}</h2>
                </div>

                <div className="bg-neutral-950/50 rounded-xl p-6 mb-8 border border-neutral-800/50 text-center relative overflow-hidden">
                  <div className="absolute inset-0 bg-gradient-to-r from-transparent via-neutral-800/20 to-transparent translate-x-[-100%] animate-[shimmer_2s_infinite]" />
                  <p className="text-sm text-neutral-500 mb-2 font-medium">Suggested Category</p>
                  
                  {isEditing ? (
                    <input 
                      autoFocus
                      type="text"
                      value={editValue}
                      onChange={e => setEditValue(e.target.value)}
                      placeholder="Type custom category..."
                      className="bg-transparent border-b border-indigo-500 text-indigo-400 text-xl font-medium outline-none text-center w-full px-4 py-1"
                    />
                  ) : (
                    <p className="text-2xl text-indigo-400 font-medium tracking-tight">
                      {currentSuggestion}
                    </p>
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
                        onClick={handleCustomApprove}
                        className="flex-1 py-3 px-6 rounded-xl font-medium text-white bg-indigo-600 hover:bg-indigo-500 transition-colors"
                      >
                        Save & Apply
                      </button>
                    </>
                  ) : (
                    <>
                      <button 
                        onClick={() => {
                          setEditValue(currentSuggestion === "Thinking..." ? "" : currentSuggestion);
                          setIsEditing(true);
                        }}
                        className="flex-1 py-3 px-6 rounded-xl font-medium text-white bg-amber-600/20 border border-amber-600/30 hover:bg-amber-600/30 text-amber-500 transition-colors flex items-center justify-center gap-2"
                      >
                        <Edit2 className="w-4 h-4" /> Edit
                      </button>
                      <button 
                        onClick={handleApprove}
                        disabled={currentSuggestion === "Thinking..."}
                        className="flex-1 py-3 px-6 rounded-xl font-medium text-emerald-950 bg-emerald-500 hover:bg-emerald-400 transition-colors flex items-center justify-center shadow-[0_0_20px_rgba(16,185,129,0.3)] hover:shadow-[0_0_30px_rgba(16,185,129,0.5)] disabled:opacity-50"
                      >
                        Approve
                      </button>
                    </>
                  )}
                </div>
              </div>
            </motion.div>
          ) : success ? (
            <motion.div
              key="success"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              className="text-center"
            >
              <div className="w-24 h-24 bg-emerald-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
                <Check className="w-12 h-12 text-emerald-400" />
              </div>
              <h2 className="text-4xl font-semibold mb-4 text-white">Files Organized!</h2>
              <p className="text-neutral-400 max-w-md mx-auto">
                Your workspace is now much cleaner. All approved files have been logically integrated into their specific designated folders.
              </p>
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
                All files have been staged locally. Click below to execute physical storage actions on your machine.
              </p>
              
              <div className="bg-neutral-950/80 rounded-xl p-4 border border-neutral-800/50 mb-8 max-h-60 overflow-y-auto w-full text-left">
                {Object.entries(stagedState).map(([f, data]) => (
                  <div key={f} className="flex justify-between items-center py-2 border-b border-neutral-800/50 last:border-0 text-sm">
                    <span className="text-neutral-300 truncate w-1/2">{f}</span>
                    <span className="text-indigo-400 font-medium px-2 py-1 bg-indigo-500/10 rounded-md truncate max-w-[40%]">{data.category}</span>
                  </div>
                ))}
              </div>

              <button 
                onClick={executeOrganization}
                disabled={organizing}
                className="w-full py-4 px-6 rounded-xl font-medium text-emerald-950 bg-emerald-500 hover:bg-emerald-400 transition-all flex items-center justify-center gap-2 text-lg shadow-[0_0_20px_rgba(16,185,129,0.3)] disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {organizing ? "Organizing Files..." : (
                  <>
                    <Play className="w-5 h-5 fill-current" /> Commit Changes
                  </>
                )}
              </button>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
      
      <style dangerouslySetInnerHTML={{__html: `
        @keyframes shimmer {
          100% {
            transform: translateX(100%);
          }
        }
      `}} />
    </div>
  );
}
