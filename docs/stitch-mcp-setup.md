# Google Stitch MCP setup

This repository configures Google Stitch as a workspace-level Model Context
Protocol (MCP) server for VS Code. The configuration is stored in
`.vscode/mcp.json`, which VS Code automatically discovers when this repository
is opened as a workspace.

## Configuration

The `stitch` server uses:

- HTTP transport
- `https://stitch.googleapis.com/mcp` as the remote endpoint
- `Accept: application/json`
- `X-Goog-Api-Key` for authentication

The configuration shape is:

```json
{
  "servers": {
    "stitch": {
      "url": "https://stitch.googleapis.com/mcp",
      "type": "http",
      "headers": {
        "Accept": "application/json",
        "X-Goog-Api-Key": "REPLACE_WITH_STITCH_API_KEY"
      }
    }
  }
}
```

The repository's local `.vscode/mcp.json` has already had the placeholder
replaced with the supplied Stitch API key.

## Replace or rotate the API key

1. Obtain a valid Google Stitch API key from the Google account or Google Cloud
   project authorized to use Stitch.
2. Open `.vscode/mcp.json`.
3. Replace the value of `X-Goog-Api-Key` with the new key:

   ```json
   "X-Goog-Api-Key": "YOUR_VALID_STITCH_API_KEY"
   ```

4. Save the file.
5. In VS Code, run **MCP: List Servers**, select **stitch**, and restart the
   server so the updated header is used.

API keys are credentials. Do not paste this file into tickets, logs, prompts,
or public repositories. VS Code recommends using input variables or environment
files instead of hardcoding secrets when a configuration will be shared. If
this repository will be published, rotate the supplied key and migrate the
header value to a secure local input before committing.

## Verify MCP connectivity in VS Code

1. Open the repository root in a current version of VS Code.
2. Open `.vscode/mcp.json`. Confirm that VS Code recognizes the MCP schema and
   shows no JSON or configuration diagnostics.
3. Open the Command Palette with `Ctrl+Shift+P`.
4. Run **MCP: List Servers**.
5. Select **stitch**, then choose **Start** or **Restart**.
6. Accept the workspace/server trust prompt after reviewing the endpoint.
7. Open Chat, select **Configure Tools**, and confirm that Stitch tools are
   listed and enabled.
8. Send a small test request, such as:

   > Use Stitch to list the UI generation capabilities available to this
   > workspace.

If the server fails to connect, run **MCP: List Servers**, select **stitch**,
and choose **Show Output**. Check for an invalid API key, authorization error,
network restriction, or an incorrect endpoint.

## Use Stitch MCP from coding agents

An MCP-aware coding agent running in VS Code can use the tools exposed by the
`stitch` server after the server is started and its tools are enabled. In the
prompt:

1. Explicitly ask the agent to use Stitch.
2. Describe the screen, target framework, layout, states, and responsive
   behavior.
3. Request React components and Tailwind CSS-compatible styling.
4. Ask the agent to inspect the existing frontend conventions before applying
   generated code.
5. Review and approve tool calls and generated changes before accepting them.

Tool availability varies with the capabilities returned by the Stitch server.
If an agent does not use Stitch automatically, open **Configure Tools**, enable
the Stitch tools, and mention the relevant Stitch tool in the prompt.

## Example React + Tailwind prompts

### Student food ordering home

> Use Stitch MCP to design a responsive React + Tailwind student food-ordering
> home screen. Include a campus selector, search, cuisine filters, featured
> canteens, popular dishes, dietary badges, delivery-time estimates, and a
> mobile bottom navigation. Produce accessible components with loading, empty,
> and error states. Match the existing repository's component conventions.

### Canteen menu

> Use Stitch MCP to generate a React + Tailwind canteen menu screen for a smart
> campus app. Include canteen status, pickup wait time, category tabs, item
> cards, vegetarian indicators, customization controls, an add-to-cart action,
> and a sticky cart summary. Make it responsive and keyboard accessible.

### Checkout and order tracking

> Use Stitch MCP to create React + Tailwind screens for checkout and live order
> tracking. Include pickup location, order summary, payment selection, pricing
> breakdown, preparation progress, estimated pickup time, order number, and
> cancellation/help actions. Include realistic validation and status states.

### Campus vendor dashboard

> Use Stitch MCP to design a desktop-first React + Tailwind vendor dashboard.
> Include incoming orders, preparation queues, menu availability toggles,
> low-stock alerts, daily revenue, peak-hour charts, and responsive tablet
> behavior. Use accessible tables, cards, dialogs, and status colors.

## References

- [Google Stitch MCP documentation](https://stitch.withgoogle.com/docs/mcp)
- [VS Code: Add and manage MCP servers](https://code.visualstudio.com/docs/agent-customization/mcp-servers)
