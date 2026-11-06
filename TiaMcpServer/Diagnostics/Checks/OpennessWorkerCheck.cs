using TiaMcpServer.Cli;
using TiaMcpServer.Worker;

namespace TiaMcpServer.Diagnostics.Checks;

public sealed class OpennessWorkerCheck : IDiagnosticCheck
{
    internal static readonly string[] RequiredCompanionFiles =
    {
        "TiaMcpServer.OpennessWorker.exe.config",
        "TiaMcpServer.Contracts.dll",
        "Microsoft.Bcl.AsyncInterfaces.dll",
        "System.Buffers.dll",
        "System.Memory.dll",
        "System.Numerics.Vectors.dll",
        "System.IO.Pipelines.dll",
        "System.Runtime.CompilerServices.Unsafe.dll",
        "System.Text.Encodings.Web.dll",
        "System.Text.Json.dll",
        "System.Threading.Tasks.Extensions.dll",
        "System.ValueTuple.dll"
    };

    private readonly IApplicationInfoService _appInfo;
    private readonly IFileSystemService _fileSystem;
    private readonly WorkerPathParseResult? _workerSelection;

    public OpennessWorkerCheck(
        IApplicationInfoService appInfo,
        IFileSystemService fileSystem,
        WorkerPathParseResult? workerSelection = null)
    {
        _appInfo = appInfo;
        _fileSystem = fileSystem;
        _workerSelection = workerSelection;
    }

    public string Id => "openness-worker";
    public string Name => "Openness worker";

    public DiagnosticCheckResult Run()
    {
        var evidence = Evidence.Empty();

        if (_workerSelection?.IsMock == true)
        {
            evidence["isMock"] = "true";
            evidence["workerSelectionSource"] = _workerSelection.Source.ToString();

            var mockPath = _workerSelection.WorkerPath;
            if (mockPath is null || !_fileSystem.FileExists(mockPath))
            {
                var fakeResult = OpennessWorkerLocator.LocateFakeWorker(_appInfo.BaseDirectory, _fileSystem);
                for (int i = 0; i < fakeResult.Candidates.Count; i++)
                {
                    var candidate = fakeResult.Candidates[i];
                    evidence[$"candidate[{i}].path"] = candidate.Path;
                    evidence[$"candidate[{i}].exists"] = candidate.Exists.ToString().ToLowerInvariant();
                }

                return new DiagnosticCheckResult(
                    Id,
                    Name,
                    DiagnosticStatus.Failed,
                    "Mock worker executable (TiaMcpServer.FakeWorker.exe) was not found.",
                    "Build the solution and ensure TiaMcpServer.FakeWorker is built before running in mock mode.",
                    evidence);
            }

            evidence["selectedPath"] = mockPath;
            var mockVersion = _fileSystem.GetFileVersion(mockPath);
            evidence["workerVersion"] = mockVersion;

            var mockMessage = mockVersion is not null
                ? $"Mock worker found at {mockPath} (version {mockVersion}, mock mode enabled)."
                : $"Mock worker found at {mockPath} (mock mode enabled).";

            return new DiagnosticCheckResult(
                Id,
                Name,
                DiagnosticStatus.Passed,
                mockMessage,
                null,
                evidence);
        }

        if (_workerSelection?.WorkerPath is not null)
        {
            evidence["workerSelectionSource"] = _workerSelection.Source.ToString();
            var overridePath = _workerSelection.WorkerPath;
            evidence["selectedPath"] = overridePath;

            if (!_fileSystem.FileExists(overridePath))
            {
                return new DiagnosticCheckResult(
                    Id,
                    Name,
                    DiagnosticStatus.Failed,
                    $"Specified worker executable was not found at '{overridePath}'.",
                    "Ensure the specified worker path points to a valid executable.",
                    evidence);
            }

            var overrideVersion = _fileSystem.GetFileVersion(overridePath);
            evidence["workerVersion"] = overrideVersion;

            var overrideMessage = overrideVersion is not null
                ? $"Worker found at {overridePath} (version {overrideVersion}, override enabled)."
                : $"Worker found at {overridePath} (override enabled).";

            return new DiagnosticCheckResult(
                Id,
                Name,
                DiagnosticStatus.Passed,
                overrideMessage,
                null,
                evidence);
        }

        var result = OpennessWorkerLocator.Locate(_appInfo.BaseDirectory, _fileSystem);

        for (int i = 0; i < result.Candidates.Count; i++)
        {
            var candidate = result.Candidates[i];
            evidence[$"candidate[{i}].path"] = candidate.Path;
            evidence[$"candidate[{i}].exists"] = candidate.Exists.ToString().ToLowerInvariant();
        }

        if (!result.Found || result.SelectedPath is null)
        {
            return new DiagnosticCheckResult(
                Id,
                Name,
                DiagnosticStatus.Failed,
                "TIA Openness worker executable was not found.",
                "Build the solution and ensure the openness-worker folder is beside the MCP server executable, or reinstall the tia-mcp global tool.",
                evidence);
        }

        var path = result.SelectedPath;
        evidence["selectedPath"] = path;

        var version = _fileSystem.GetFileVersion(path);
        evidence["workerVersion"] = version;

        var directory = Path.GetDirectoryName(path);
        if (directory is null)
        {
            return new DiagnosticCheckResult(
                Id,
                Name,
                DiagnosticStatus.Failed,
                $"Worker executable found at {path} but its directory could not be determined.",
                "Rebuild the solution or reinstall the tia-mcp global tool.",
                evidence);
        }

        var missingCompanionFiles = new List<string>();
        foreach (var companionFile in RequiredCompanionFiles)
        {
            var companionPath = Path.Combine(directory, companionFile);
            var exists = _fileSystem.FileExists(companionPath);
            evidence[$"companion.{companionFile}.path"] = companionPath;
            evidence[$"companion.{companionFile}.exists"] = exists.ToString().ToLowerInvariant();
            if (!exists)
            {
                missingCompanionFiles.Add(companionFile);
            }
        }

        if (missingCompanionFiles.Count > 0)
        {
            return new DiagnosticCheckResult(
                Id,
                Name,
                DiagnosticStatus.Failed,
                $"Worker executable found at {path} but required companion files are missing: {string.Join(", ", missingCompanionFiles)}.",
                "Rebuild the solution or reinstall the tia-mcp global tool; the openness-worker folder is incomplete.",
                evidence);
        }

        var message = version is not null
            ? $"Worker found at {path} (version {version})."
            : $"Worker found at {path}.";

        return new DiagnosticCheckResult(
            Id,
            Name,
            DiagnosticStatus.Passed,
            message,
            null,
            evidence);
    }
}
