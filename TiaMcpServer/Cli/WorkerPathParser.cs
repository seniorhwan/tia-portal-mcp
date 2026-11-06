using TiaMcpServer.Diagnostics;
using TiaMcpServer.Worker;

namespace TiaMcpServer.Cli;

public enum WorkerSelectionSource
{
    Default,
    WorkerPathOption,
    WorkerPathEnvironment,
    MockOption,
    MockEnvironment
}

public sealed record WorkerPathParseResult(
    bool IsValid,
    string? WorkerPath,
    bool IsMock,
    WorkerSelectionSource Source,
    string? Error)
{
    public static WorkerPathParseResult Ok(
        string? workerPath,
        bool isMock,
        WorkerSelectionSource source)
        => new(true, workerPath, isMock, source, null);

    public static WorkerPathParseResult Fail(
        string error,
        WorkerSelectionSource source)
        => new(false, null, false, source, error);
}

public static class WorkerPathParser
{
    public const string MockFlag = "--mock";
    public const string WorkerPathFlag = "--worker-path";
    public const string WorkerPathEnvVar = "TIA_MCP_WORKER_PATH";
    public const string UseFakeWorkerEnvVar = "TIA_MCP_USE_FAKE_WORKER";

    public static WorkerPathParseResult Parse(
        string[] args,
        Func<string, string?>? getEnvironmentVariable = null,
        IFileSystemService? fileSystem = null,
        string? baseDirectory = null)
    {
        getEnvironmentVariable ??= Environment.GetEnvironmentVariable;
        fileSystem ??= FileSystemService.Instance;
        baseDirectory ??= AppContext.BaseDirectory;

        // 1. Check CLI --worker-path
        var workerPathOption = StartupOptionReader.ReadSingle(args, WorkerPathFlag);
        if (workerPathOption.Error is not null)
        {
            return WorkerPathParseResult.Fail(workerPathOption.Error, WorkerSelectionSource.WorkerPathOption);
        }

        if (workerPathOption.Value is not null)
        {
            var explicitPath = workerPathOption.Value.Trim();
            if (!fileSystem.FileExists(explicitPath))
            {
                return WorkerPathParseResult.Fail(
                    $"Worker executable was not found at '{explicitPath}'.",
                    WorkerSelectionSource.WorkerPathOption);
            }

            var isMockWithExplicitPath = args.Any(arg => string.Equals(arg, MockFlag, StringComparison.OrdinalIgnoreCase))
                || IsTruthy(getEnvironmentVariable(UseFakeWorkerEnvVar));

            return WorkerPathParseResult.Ok(
                explicitPath,
                isMock: isMockWithExplicitPath,
                WorkerSelectionSource.WorkerPathOption);
        }

        // 2. Check Environment Variable TIA_MCP_WORKER_PATH
        var envWorkerPath = getEnvironmentVariable(WorkerPathEnvVar);
        if (!string.IsNullOrWhiteSpace(envWorkerPath))
        {
            var trimmedEnv = envWorkerPath.Trim();
            if (!fileSystem.FileExists(trimmedEnv))
            {
                return WorkerPathParseResult.Fail(
                    $"Worker executable specified by {WorkerPathEnvVar} was not found at '{trimmedEnv}'.",
                    WorkerSelectionSource.WorkerPathEnvironment);
            }

            var isMockWithEnvPath = args.Any(arg => string.Equals(arg, MockFlag, StringComparison.OrdinalIgnoreCase))
                || IsTruthy(getEnvironmentVariable(UseFakeWorkerEnvVar));

            return WorkerPathParseResult.Ok(
                trimmedEnv,
                isMock: isMockWithEnvPath,
                WorkerSelectionSource.WorkerPathEnvironment);
        }

        // 3. Check CLI --mock
        var hasMockFlag = args.Any(arg => string.Equals(arg, MockFlag, StringComparison.OrdinalIgnoreCase));
        if (hasMockFlag)
        {
            var fakeLocation = OpennessWorkerLocator.LocateFakeWorker(baseDirectory, fileSystem);
            if (!fakeLocation.Found || fakeLocation.SelectedPath is null)
            {
                return WorkerPathParseResult.Fail(
                    "Mock worker executable (TiaMcpServer.FakeWorker.exe) was not found. Build the solution before running in mock mode.",
                    WorkerSelectionSource.MockOption);
            }

            return WorkerPathParseResult.Ok(
                fakeLocation.SelectedPath,
                isMock: true,
                WorkerSelectionSource.MockOption);
        }

        // 4. Check Environment Variable TIA_MCP_USE_FAKE_WORKER
        var envUseFake = getEnvironmentVariable(UseFakeWorkerEnvVar);
        if (IsTruthy(envUseFake))
        {
            var fakeLocation = OpennessWorkerLocator.LocateFakeWorker(baseDirectory, fileSystem);
            if (!fakeLocation.Found || fakeLocation.SelectedPath is null)
            {
                return WorkerPathParseResult.Fail(
                    "Mock worker executable (TiaMcpServer.FakeWorker.exe) was not found. Build the solution before running in mock mode.",
                    WorkerSelectionSource.MockEnvironment);
            }

            return WorkerPathParseResult.Ok(
                fakeLocation.SelectedPath,
                isMock: true,
                WorkerSelectionSource.MockEnvironment);
        }

        // 5. Default: Live Openness worker
        return WorkerPathParseResult.Ok(
            null,
            isMock: false,
            WorkerSelectionSource.Default);
    }

    private static bool IsTruthy(string? value)
    {
        if (string.IsNullOrWhiteSpace(value))
        {
            return false;
        }

        var trimmed = value.Trim();
        return string.Equals(trimmed, "1", StringComparison.OrdinalIgnoreCase)
            || string.Equals(trimmed, "true", StringComparison.OrdinalIgnoreCase)
            || string.Equals(trimmed, "yes", StringComparison.OrdinalIgnoreCase);
    }
}
