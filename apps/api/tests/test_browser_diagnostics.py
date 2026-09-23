from app.agent.report import browser_findings


def test_browser_findings_are_tied_to_the_step_that_produced_them():
    findings, accessibility_measured, performance_measured = browser_findings(
        [
            {
                "url": "https://fixture.test/signup",
                "diagnostics": {
                    "accessibility": {
                        "status": "complete",
                        "total": 1,
                        "issues": [
                            {
                                "rule": "label",
                                "severity": "high",
                                "message": "Form elements must have labels",
                                "target": "#email",
                            }
                        ],
                    },
                    "web_vitals": {"lcp_ms": 4300, "cls": 0.04, "inp_ms": 120},
                },
            }
        ]
    )

    assert accessibility_measured is True
    assert performance_measured is True
    assert [(finding.kind, finding.severity) for finding in findings] == [
        ("accessibility", "high"),
        ("performance", "high"),
    ]
    assert all(finding.evidence and "step 1" in finding.evidence for finding in findings)
