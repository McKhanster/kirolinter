const core = require('@actions/core');
const github = require('@actions/github');
const exec = require('@actions/exec');
const fs = require('fs-extra');
const path = require('path');
const axios = require('axios');
const yaml = require('js-yaml');

class KiroLinterDevOpsAction {
  constructor() {
    this.config = this.parseInputs();
    this.octokit = github.getOctokit(core.getInput('github-token'));
    this.context = github.context;
  }

  parseInputs() {
    return {
      gateType: core.getInput('gate-type') || 'pre-merge',
      riskAssessment: core.getBooleanInput('risk-assessment'),
      deploymentAnalysis: core.getBooleanInput('deployment-analysis'),
      failOnIssues: core.getBooleanInput('fail-on-issues'),
      severityThreshold: core.getInput('severity-threshold') || 'medium',
      timeout: parseInt(core.getInput('timeout')) || 300,
      outputFormat: core.getInput('output-format') || 'markdown',
      createPrComment: core.getBooleanInput('create-pr-comment'),
      createCheckRun: core.getBooleanInput('create-check-run'),
      configPath: core.getInput('config-path') || '.kirolinter.yml',
      endpoint: core.getInput('kirolinter-endpoint') || 'https://api.kirolinter.dev',
      token: core.getInput('kirolinter-token')
    };
  }

  async run() {
    try {
      core.info(`🚀 Starting KiroLinter DevOps Quality Gate - ${this.config.gateType}`);
      
      // Create check run if requested
      let checkRun = null;
      if (this.config.createCheckRun) {
        checkRun = await this.createCheckRun();
        core.info(`✅ Created check run: ${checkRun.data.html_url}`);
      }

      // Load configuration
      const config = await this.loadConfiguration();
      
      // Run quality analysis
      const result = await this.runQualityAnalysis(config);

      // Update check run with results
      if (checkRun) {
        await this.updateCheckRun(checkRun.data.id, result);
        core.setOutput('check-run-id', checkRun.data.id);
      }

      // Create PR comment if requested
      if (this.config.createPrComment && this.context.payload.pull_request) {
        await this.createPrComment(result);
        core.info('✅ Created PR comment with quality report');
      }

      // Set outputs
      this.setOutputs(result);

      // Generate SARIF report
      if (this.config.outputFormat === 'sarif') {
        const sarifPath = await this.generateSarifReport(result);
        core.setOutput('sarif-file', sarifPath);
      }

      // Determine success/failure
      if (this.config.failOnIssues && !result.passed) {
        core.setFailed(`Quality gate failed: ${result.criticalIssues} critical, ${result.highIssues} high severity issues found`);
      } else {
        core.info(`✅ Quality gate passed! Score: ${result.qualityScore}/100`);
      }

    } catch (error) {
      core.setFailed(`Action failed: ${error.message}`);
    }
  }

  async loadConfiguration() {
    try {
      if (await fs.pathExists(this.config.configPath)) {
        const configContent = await fs.readFile(this.config.configPath, 'utf8');
        return yaml.load(configContent);
      } else {
        core.info(`ℹ️ No configuration file found at ${this.config.configPath}, using defaults`);
        return {};
      }
    } catch (error) {
      core.warning(`Failed to load configuration: ${error}`);
      return {};
    }
  }

  async runQualityAnalysis(config) {
    core.info('🔍 Running quality analysis...');

    try {
      // Check if KiroLinter is available locally
      const isLocal = await this.checkLocalKiroLinter();
      
      if (isLocal) {
        return await this.runLocalAnalysis(config);
      } else if (this.config.token) {
        return await this.runCloudAnalysis(config);
      } else {
        // Install and run KiroLinter
        return await this.installAndRunKiroLinter(config);
      }
    } catch (error) {
      core.error(`Analysis failed: ${error}`);
      throw error;
    }
  }

  async checkLocalKiroLinter() {
    try {
      let exitCode = 0;
      await exec.exec('kirolinter', ['--version'], {
        listeners: {
          stdout: (data) => {
            core.info(`KiroLinter version: ${data.toString()}`);
          }
        },
        ignoreReturnCode: true
      }).then((code) => {
        exitCode = code;
      });
      return exitCode === 0;
    } catch {
      return false;
    }
  }

  async installAndRunKiroLinter(config) {
    core.info('📦 Installing KiroLinter...');
    
    // Install KiroLinter from current directory in editable mode
    await exec.exec('pip', ['install', '-e', '.']);
    
    return await this.runLocalAnalysis(config);
  }

  async runLocalAnalysis(config) {
    core.info('🔍 Running local KiroLinter analysis...');

    const args = [
      'devops',
      'gate',
      '--type', this.config.gateType,
      '--format', 'json',
      '--severity-threshold', this.config.severityThreshold
    ];

    if (this.config.riskAssessment) {
      args.push('--risk-assessment');
    }

    if (this.config.deploymentAnalysis) {
      args.push('--deployment-analysis');
    }

    if (this.config.configPath && await fs.pathExists(this.config.configPath)) {
      args.push('--config', this.config.configPath);
    }

    let output = '';
    await exec.exec('kirolinter', args, {
      listeners: {
        stdout: (data) => {
          output += data.toString();
        },
        stderr: (data) => {
          core.warning(data.toString());
        }
      },
      ignoreReturnCode: true
    });

    try {
      const result = JSON.parse(output);
      return this.normalizeResult(result);
    } catch (error) {
      throw new Error(`Failed to parse KiroLinter output: ${error}`);
    }
  }

  async runCloudAnalysis(config) {
    core.info('☁️ Running cloud KiroLinter analysis...');

    const payload = {
      gateType: this.config.gateType,
      repository: this.context.repo,
      ref: this.context.sha,
      pullRequest: this.context.payload.pull_request?.number,
      config: config,
      options: {
        riskAssessment: this.config.riskAssessment,
        deploymentAnalysis: this.config.deploymentAnalysis,
        severityThreshold: this.config.severityThreshold
      }
    };

    const response = await axios.post(`${this.config.endpoint}/v1/quality-gate`, payload, {
      headers: {
        'Authorization': `Bearer ${this.config.token}`,
        'Content-Type': 'application/json',
        'User-Agent': 'KiroLinter-GitHub-Action/1.0.0'
      },
      timeout: this.config.timeout * 1000
    });

    return this.normalizeResult(response.data);
  }

  normalizeResult(rawResult) {
    return {
      qualityScore: rawResult.quality_score || rawResult.qualityScore || 0,
      issuesFound: rawResult.issues_found || rawResult.issuesFound || 0,
      criticalIssues: rawResult.critical_issues || rawResult.criticalIssues || 0,
      highIssues: rawResult.high_issues || rawResult.highIssues || 0,
      mediumIssues: rawResult.medium_issues || rawResult.mediumIssues || 0,
      lowIssues: rawResult.low_issues || rawResult.lowIssues || 0,
      riskScore: rawResult.risk_score || rawResult.riskScore || 0,
      passed: rawResult.passed || (rawResult.quality_score || rawResult.qualityScore || 0) >= 70,
      reportUrl: rawResult.report_url || rawResult.reportUrl,
      issues: rawResult.issues || [],
      recommendations: rawResult.recommendations || []
    };
  }

  async createCheckRun() {
    return await this.octokit.rest.checks.create({
      owner: this.context.repo.owner,
      repo: this.context.repo.repo,
      name: `KiroLinter DevOps - ${this.config.gateType.replace('_', ' ')}`,
      head_sha: this.context.sha,
      status: 'in_progress',
      started_at: new Date().toISOString(),
      details_url: 'https://kirolinter.dev'
    });
  }

  async updateCheckRun(checkRunId, result) {
    const conclusion = result.passed ? 'success' : 'failure';
    const title = result.passed ? '✅ Quality Gate Passed' : '❌ Quality Gate Failed';
    
    const summary = this.generateCheckRunSummary(result);

    await this.octokit.rest.checks.update({
      owner: this.context.repo.owner,
      repo: this.context.repo.repo,
      check_run_id: checkRunId,
      status: 'completed',
      conclusion: conclusion,
      completed_at: new Date().toISOString(),
      output: {
        title: title,
        summary: summary,
        text: this.generateDetailedReport(result)
      }
    });
  }

  generateCheckRunSummary(result) {
    return `
**Quality Score**: ${result.qualityScore}/100
**Risk Score**: ${result.riskScore}/100

**Issues Found**: ${result.issuesFound}
- Critical: ${result.criticalIssues}
- High: ${result.highIssues}  
- Medium: ${result.mediumIssues}
- Low: ${result.lowIssues}

**Gate Type**: ${this.config.gateType.replace('_', ' ')}
**Result**: ${result.passed ? 'PASSED' : 'FAILED'}
    `.trim();
  }

  generateDetailedReport(result) {
    let report = `## 📊 Detailed Quality Report\n\n`;
    
    if (result.issues.length > 0) {
      report += `### Issues Found\n\n`;
      
      const groupedIssues = result.issues.reduce((acc, issue) => {
        if (!acc[issue.severity]) acc[issue.severity] = [];
        acc[issue.severity].push(issue);
        return acc;
      }, {});

      for (const [severity, issues] of Object.entries(groupedIssues)) {
        if (issues.length === 0) continue;
        
        report += `#### ${severity.toUpperCase()} Issues (${issues.length})\n\n`;
        
        for (const issue of issues.slice(0, 10)) { // Limit to first 10 per severity
          report += `- **${issue.rule || issue.category}**: ${issue.message}\n`;
          report += `  - File: \`${issue.file}:${issue.line}\`\n\n`;
        }
        
        if (issues.length > 10) {
          report += `... and ${issues.length - 10} more ${severity} issues\n\n`;
        }
      }
    }

    if (result.recommendations && result.recommendations.length > 0) {
      report += `### 🎯 Recommendations\n\n`;
      result.recommendations.slice(0, 5).forEach((rec, index) => {
        report += `${index + 1}. ${rec}\n`;
      });
    }

    return report;
  }

  async createPrComment(result) {
    const body = this.generatePrComment(result);
    
    await this.octokit.rest.issues.createComment({
      owner: this.context.repo.owner,
      repo: this.context.repo.repo,
      issue_number: this.context.payload.pull_request.number,
      body: body
    });
  }

  generatePrComment(result) {
    const statusEmoji = result.passed ? '✅' : '❌';
    const scoreColor = result.qualityScore >= 80 ? '🟢' : result.qualityScore >= 60 ? '🟡' : '🔴';
    
    return `
## ${statusEmoji} KiroLinter DevOps Quality Report

**Quality Score**: ${scoreColor} ${result.qualityScore}/100  
**Risk Score**: ${result.riskScore}/100  
**Gate**: ${this.config.gateType.replace('_', ' ')}  

### 📈 Issue Summary
- **Critical**: ${result.criticalIssues}
- **High**: ${result.highIssues}  
- **Medium**: ${result.mediumIssues}
- **Low**: ${result.lowIssues}

${result.passed ? 
  '🎉 **Quality gate passed!** Your code meets the required quality standards.' : 
  '⚠️ **Quality gate failed.** Please address the issues above before merging.'
}

---
*Generated by [KiroLinter DevOps](https://kirolinter.dev) • [View detailed report](${result.reportUrl || '#'})*
    `.trim();
  }

  async generateSarifReport(result) {
    const sarifReport = {
      version: '2.1.0',
      $schema: 'https://json.schemastore.org/sarif-2.1.0.json',
      runs: [{
        tool: {
          driver: {
            name: 'KiroLinter DevOps',
            version: '1.0.0',
            informationUri: 'https://kirolinter.dev',
            rules: []
          }
        },
        results: result.issues.map(issue => ({
          ruleId: issue.rule || issue.category,
          level: this.mapSeverityToSarifLevel(issue.severity),
          message: {
            text: issue.message
          },
          locations: [{
            physicalLocation: {
              artifactLocation: {
                uri: issue.file
              },
              region: {
                startLine: issue.line
              }
            }
          }]
        }))
      }]
    };

    const sarifPath = path.join(process.cwd(), 'kirolinter-results.sarif');
    await fs.writeJSON(sarifPath, sarifReport, { spaces: 2 });
    
    return sarifPath;
  }

  mapSeverityToSarifLevel(severity) {
    switch (severity.toLowerCase()) {
      case 'critical':
        return 'error';
      case 'high':
        return 'error';
      case 'medium':
        return 'warning';
      case 'low':
        return 'note';
      default:
        return 'warning';
    }
  }

  setOutputs(result) {
    core.setOutput('quality-score', result.qualityScore.toString());
    core.setOutput('issues-found', result.issuesFound.toString());
    core.setOutput('critical-issues', result.criticalIssues.toString());
    core.setOutput('high-issues', result.highIssues.toString());
    core.setOutput('medium-issues', result.mediumIssues.toString());
    core.setOutput('low-issues', result.lowIssues.toString());
    core.setOutput('risk-score', result.riskScore.toString());
    core.setOutput('passed', result.passed.toString());
    
    if (result.reportUrl) {
      core.setOutput('report-url', result.reportUrl);
    }
  }
}

// Run the action
async function run() {
  const action = new KiroLinterDevOpsAction();
  await action.run();
}

run().catch(error => {
  core.setFailed(error.message);
});