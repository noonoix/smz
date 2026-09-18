using System.Runtime.CompilerServices;
using Ams.UI.Models;
using Ams.UI.Services;

internal static class LightStateProfileMigrationContract
{
    [ModuleInitializer]
    internal static void Execute()
    {
        var defaults = LightStateDefaults.CreateInitialProfiles();
        var legacy = defaults.Where(p => p.Id != "login-or-dc").ToList();
        legacy.Single(p => p.Id == "game").LuxCenter = 27.25;
        legacy.Single(p => p.Id == "targeted").LuxTolerance = 3.5;

        var migrated = LightStateProfileStore.Normalize(legacy);
        var login = migrated.Single(p => p.Id == "login-or-dc");
        if (migrated.Count(p => p.Id == "login-or-dc") != 1
            || migrated.Select(p => p.Id).Take(6).SequenceEqual(new[]
            {
                "desktop", "login-or-dc", "character-dashboard",
                "entering-game-loading", "game", "targeted",
            }) == false
            || migrated.Single(p => p.Id == "game").LuxCenter != 27.25
            || migrated.Single(p => p.Id == "targeted").LuxTolerance != 3.5
            || login.Name != "صفحه لاگین یا DC")
            throw new InvalidOperationException("Five-profile migration did not restore the canonical six-profile order.");

        Console.WriteLine("PASS: v32 five-profile storage migrates to six canonical Guard profiles");
    }
}
