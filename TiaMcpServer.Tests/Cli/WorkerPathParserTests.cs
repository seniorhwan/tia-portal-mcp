using TiaMcpServer.Cli;
using TiaMcpServer.Tests.Diagnostics;
using Xunit;

namespace TiaMcpServer.Tests.Cli;

public class WorkerPathParserTests
{
    private readonly FakeFileSystemService _fileSystem = new();
    private readonly string _baseDir = @"C:\app";

    private WorkerPathParseResult Parse(
        string[] args,
        string? workerPathEnv = null,
        string? useFakeEnv = null)
    {
        return WorkerPathParser.Parse(
            args,
            name => name switch
            {
                WorkerPathParser.WorkerPathEnvVar => workerPathEnv,
                WorkerPathParser.UseFakeWorkerEnvVar => useFakeEnv,
                _ => null
            },
            _fileSystem,
            _baseDir);
    }

    [Theory]
    [InlineData(null, null)]
    [InlineData("", "")]
    [InlineData("   ", "0")]
    public void ReturnsDefaultWhenNeitherSet(string? workerPathEnv, string? useFakeEnv)
    {
        var result = Parse([], workerPathEnv, useFakeEnv);

        Assert.True(result.IsValid, result.Error);
        Assert.Null(result.WorkerPath);
        Assert.False(result.IsMock);
        Assert.Equal(WorkerSelectionSource.Default, result.Source);
        Assert.Null(result.Error);
    }

    [Theory]
    [InlineData("--worker-path", @"C:\custom\worker.exe")]
    [InlineData(@"--worker-path=C:\custom\worker.exe")]
    [InlineData("--WORKER-PATH", @"C:\custom\worker.exe")]
    [InlineData(@"--WORKER-PATH=C:\custom\worker.exe")]
    public void ReadsCommandLineWorkerPath(params string[] args)
    {
        var expectedPath = @"C:\custom\worker.exe";
        _fileSystem.AddFile(expectedPath);

        var result = Parse(args);

        Assert.True(result.IsValid, result.Error);
        Assert.Equal(expectedPath, result.WorkerPath);
        Assert.False(result.IsMock);
        Assert.Equal(WorkerSelectionSource.WorkerPathOption, result.Source);
        Assert.Null(result.Error);
    }

    [Theory]
    [InlineData("--worker-path")]
    [InlineData("--worker-path", "--read-only")]
    [InlineData("--worker-path=")]
    [InlineData("--worker-path", "   ")]
    public void RejectsMissingCommandLineValue(params string[] args)
    {
        var result = Parse(args);

        Assert.False(result.IsValid);
        Assert.Equal("--worker-path requires a value.", result.Error);
        Assert.Equal(WorkerSelectionSource.WorkerPathOption, result.Source);
    }

    [Fact]
    public void RejectsNonExistentCommandLinePath()
    {
        var result = Parse(["--worker-path", @"C:\missing\worker.exe"]);

        Assert.False(result.IsValid);
        Assert.Equal(@"Worker executable was not found at 'C:\missing\worker.exe'.", result.Error);
        Assert.Equal(WorkerSelectionSource.WorkerPathOption, result.Source);
    }

    [Fact]
    public void ReadsEnvironmentWorkerPath()
    {
        var path = @"C:\env\worker.exe";
        _fileSystem.AddFile(path);

        var result = Parse([], workerPathEnv: path);

        Assert.True(result.IsValid, result.Error);
        Assert.Equal(path, result.WorkerPath);
        Assert.False(result.IsMock);
        Assert.Equal(WorkerSelectionSource.WorkerPathEnvironment, result.Source);
        Assert.Null(result.Error);
    }

    [Fact]
    public void RejectsNonExistentEnvironmentWorkerPath()
    {
        var result = Parse([], workerPathEnv: @"C:\missing\env_worker.exe");

        Assert.False(result.IsValid);
        Assert.Equal(@"Worker executable specified by TIA_MCP_WORKER_PATH was not found at 'C:\missing\env_worker.exe'.", result.Error);
        Assert.Equal(WorkerSelectionSource.WorkerPathEnvironment, result.Source);
    }

    [Fact]
    public void ReadsCommandLineMockFlag()
    {
        var fakeWorkerPath = @"C:\app\fake-worker\TiaMcpServer.FakeWorker.exe";
        _fileSystem.AddFile(fakeWorkerPath);

        var result = Parse(["--mock"]);

        Assert.True(result.IsValid, result.Error);
        Assert.Equal(fakeWorkerPath, result.WorkerPath);
        Assert.True(result.IsMock);
        Assert.Equal(WorkerSelectionSource.MockOption, result.Source);
        Assert.Null(result.Error);
    }

    [Fact]
    public void RejectsMockFlagWhenFakeWorkerNotFound()
    {
        var result = Parse(["--mock"]);

        Assert.False(result.IsValid);
        Assert.Equal("Mock worker executable (TiaMcpServer.FakeWorker.exe) was not found. Build the solution before running in mock mode.", result.Error);
        Assert.Equal(WorkerSelectionSource.MockOption, result.Source);
    }

    [Theory]
    [InlineData("1")]
    [InlineData("true")]
    [InlineData("TRUE")]
    [InlineData("yes")]
    [InlineData("YES")]
    public void ReadsEnvironmentUseFakeWorker(string useFakeVal)
    {
        var fakeWorkerPath = @"C:\app\fake-worker\TiaMcpServer.FakeWorker.exe";
        _fileSystem.AddFile(fakeWorkerPath);

        var result = Parse([], useFakeEnv: useFakeVal);

        Assert.True(result.IsValid, result.Error);
        Assert.Equal(fakeWorkerPath, result.WorkerPath);
        Assert.True(result.IsMock);
        Assert.Equal(WorkerSelectionSource.MockEnvironment, result.Source);
        Assert.Null(result.Error);
    }

    [Fact]
    public void CommandLineWorkerPathWinsOverEnvironment()
    {
        var cliPath = @"C:\cli\worker.exe";
        var envPath = @"C:\env\worker.exe";
        _fileSystem.AddFile(cliPath);
        _fileSystem.AddFile(envPath);

        var result = Parse(["--worker-path", cliPath], workerPathEnv: envPath);

        Assert.True(result.IsValid, result.Error);
        Assert.Equal(cliPath, result.WorkerPath);
        Assert.Equal(WorkerSelectionSource.WorkerPathOption, result.Source);
    }

    [Fact]
    public void CommandLineWorkerPathWithMockFlagSetsIsMock()
    {
        var cliPath = @"C:\cli\mock-worker.exe";
        _fileSystem.AddFile(cliPath);

        var result = Parse(["--worker-path", cliPath, "--mock"]);

        Assert.True(result.IsValid, result.Error);
        Assert.Equal(cliPath, result.WorkerPath);
        Assert.True(result.IsMock);
        Assert.Equal(WorkerSelectionSource.WorkerPathOption, result.Source);
    }

    [Fact]
    public void HostArgumentFilterStripsMockAndWorkerPath()
    {
        var original = new[]
        {
            "--mock",
            "--worker-path",
            @"C:\custom\worker.exe",
            "--read-only",
            "--project",
            "test.ap21",
            @"--worker-path=C:\other\worker.exe"
        };

        var filtered = HostArgumentFilter.RemoveAccessModeArguments(original);

        Assert.Equal(new[] { "--project", "test.ap21" }, filtered);
    }
}
