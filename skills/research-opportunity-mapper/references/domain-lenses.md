# Composable Domain Lenses

Load only the lenses needed for a run. A domain lens adds state variables, layer bridges, confounds, baselines, and evidence gates; it does not replace the invariant opportunity test or create a favored material route.

## Contents

- [Common lens interface](#common-lens-interface)
- [Lens selection and composition](#lens-selection-and-composition)
- [Generic physical science and engineering](#generic-physical-science-and-engineering)
- [Custom domain lens](#custom-domain-lens)
- [Materials and ferroelectrics](#materials-and-ferroelectrics)
- [Multiphysics modeling](#multiphysics-modeling)
- [Semiconductor devices](#semiconductor-devices)
- [Integrated circuits](#integrated-circuits)
- [Neuromorphic systems](#neuromorphic-systems)
- [Wave and metasurface systems](#wave-and-metasurface-systems)
- [Cross-domain handoffs](#cross-domain-handoffs)
- [Evidence ceilings across layers](#evidence-ceilings-across-layers)

## Common lens interface

The agent prepares these technical slots for the selected lens; they are not
questions the user must answer one by one:

1. **Decision object**: the route, mechanism, interface, or comparison being decided.
2. **State variables**: what changes, what is controlled, and what is measured.
3. **Persistent bottleneck**: metric, regime, consequence, and evidence of persistence.
4. **Causal chain**: control -> state transition -> observable -> proposed value.
5. **Alternative explanations**: the strongest nonpreferred mechanisms or artifacts.
6. **Budgets and constraints**: energy, latency, area, bandwidth, stability, manufacturability, measurement, or other relevant limits.
7. **Baseline ladder**: physical null, conventional method, strongest practical method, and system baseline when claimed.
8. **Validation hierarchy**: simulation, component experiment, device, cell, array, circuit, architecture, and workload as applicable.
9. **Capability interface**: observed versus reported, assumed, and unknown resources.
10. **Decisive test**: control, outcome threshold, negative and ambiguous interpretations, and kill condition.

Never skip an intermediate layer merely because a lower-level result is novel. A lens must expose missing bridges, not hide them.

## Lens selection and composition

Use one primary lens and add secondary lenses only where the claim crosses an interface.

| Research object | Primary lens | Common secondary lens |
|---|---|---|
| Physical-science or engineering topic outside the specialized lenses | `generic-physical-engineering` | one specialized lens only if a real interface appears |
| User-declared domain with a fully specified Common Lens Interface | `custom` | any registered lens justified by an interface |
| Domain formation, switching, phase boundary, topology | `materials-ferroelectric` | `multiphysics-modeling` |
| Coupled PDE or phase-field mechanism study | `multiphysics-modeling` | `materials-ferroelectric` or `semiconductor-device` |
| FTJ, FeFET, transistor, diode, sensor device | `semiconductor-device` | `materials-ferroelectric`, then `integrated-circuit` if system claims appear |
| Cell/array/peripheral or chip comparison | `integrated-circuit` | `semiconductor-device` and application lens |
| Online learning, reservoir, adaptive hardware | `neuromorphic-system` | `semiconductor-device` or `integrated-circuit` |
| Tunable scattering, beam shaping, resonant surface | `wave-metasurface` | `materials-ferroelectric` or `integrated-circuit` for control electronics |

Do not load all lenses by default. Record why each lens is relevant and which layer remains outside the run boundary.

Persist the selection in `run-manifest.json`: one
`primary_domain_lens`, a duplicate-free `secondary_domain_lenses` list, and
`domain_lens_notes`. The notes may be null for a registered non-custom lens
but should state the interface rationale when secondary lenses are present.
`custom` requires substantive notes for all ten Common Lens Interface slots.
For `custom`, the persisted format is machine-readable: write each canonical
label exactly once as `Label: substantive value`, separated by a newline or
semicolon. The labels are `Decision object`, `State variables`,
`Persistent bottleneck`, `Causal chain`, `Alternative explanations`,
`Budgets and constraints`, `Baseline ladder`, `Validation hierarchy`,
`Capability interface`, and `Decisive test`. Registered Chinese label aliases
are accepted. Values are NFKC-normalized and stripped of zero-width formatting
before checking. An unlabeled summary, missing slot, `N/A`/`same as above`/`同上`
or equivalent punctuation-obscured placeholder, slot-label echo, duplicate
label, cross-slot repeated value, or nine-of-ten description is invalid in
initialization, migration, direct validation, and run-audit recomputation of a
schema-2 parent manifest.
The manifest selection is part of the run's scientific boundary; changing it
requires a declared revision rather than an unrecorded prompt-only choice.

## Generic physical science and engineering

Lens key: `generic-physical-engineering`

Use this fallback for chemistry, energy, mechanics, thermal science, general
optics, instrumentation, process engineering, or another physical/engineering
domain not yet covered by a specialized lens. Instantiate all ten Common Lens
Interface slots before search. Replace the default layer hierarchy with the
domain's actual chain (for example molecule → ensemble → reactor → process, or
material → component → structure → system) and name the governing conservation,
constitutive, kinetic, statistical, or control relations. Require the strongest
domain-native baseline, domain-specific artifacts/confounds, a matched budget,
and a quantitative bridge at every claimed scale. This lens is a complete
fallback contract, not permission to skip domain expertise.

## Custom domain lens

Lens key: `custom`

When the object, scale hierarchy, confounds or baseline ladder does not fit an
existing lens, explain the mismatch and draft a task-local lens from the request
and available evidence. The agent organizes all ten Common Lens Interface slots,
then asks only questions whose answers change the object, scope, controls or
feasibility. Confirm the proposed boundary with the configuration recommendation;
do not hand the user a ten-field questionnaire.

Persist the accepted draft in `domain_lens_notes` using the existing labeled
format. Distinguish facts, design proposals and unknowns. An unknown capability
can be specified substantively by naming the resource, its unknown access/state,
and the verification action; never invent access, measurements or results.
If a coherent custom interface cannot yet be specified, explain the missing
information and why the generic lens can govern the bounded decision. Recommend
that fallback explicitly for confirmation, rather than silently downgrading
or forcing a specialized lens.

This is customization for the current run only. Adding a permanent specialized
lens is a separate maintenance change requiring demonstrated reuse value and
explicit user authorization. Do not build a registry or persist a new library
lens as a side effect of a research run.

## Materials and ferroelectrics

Lens key: `materials-ferroelectric`

### Required causal chain

`composition/structure -> thermodynamic state landscape -> controllable stimulus -> state transition/dynamics -> structural or electrical observable -> reproducibility/stability -> device-relevant function`

For ferroelectric, ferroic, two-dimensional, and topological-state work, additionally trace:

`electrical/mechanical/thermal boundary -> polarization or order-parameter field -> domain/phase-boundary/topological descriptor -> write/hold/read behavior`

### Required state and boundary description

- composition, phase, crystal orientation, thickness, strain, interfaces, electrodes, atmosphere, and temperature;
- order parameter and state descriptor, with a precise definition;
- stimulus waveform, amplitude, rate, geometry, and duty cycle;
- spatial and temporal resolution of the observation;
- retention, reversibility, endurance, variability, and sample hierarchy;
- fabrication or sample provenance when experimental claims are made.

### Mandatory distinctions

- morphology is not automatically topology;
- average polarization is not a spatial state descriptor;
- hysteresis is not automatically ferroelectric switching;
- a simulated stable state is not experimental existence;
- a local probe result is not array-level addressability;
- a material property is not a device or system metric.

### Alternative mechanisms and confounds

Test mean polarization, ordinary domain walls, oxygen vacancies, ionic motion, charge trapping, electrochemistry, leakage, Joule heating, contact effects, surface adsorbates, strain relaxation, and measurement convolution when relevant. For topological claims, require the appropriate dimensional descriptor and a null that separates topology from visually similar closure patterns.

### Baselines and decisive evidence

Compare against a conventional uniform/domain-wall state, the same material without the proposed boundary/topology, and a mature material route under a matched observable. A decisive experiment links controlled state change to an independent readout while holding credible confounds fixed.

### Claim boundary

Without device-level validation, conclude only about material state, controllability, stability, or a bounded readout proxy. Do not claim array, computing, or circuit value.

## Multiphysics modeling

Lens key: `multiphysics-modeling`

### Required causal chain

`physical hypothesis -> governing equations/free energy -> constitutive parameters -> geometry and initial/boundary conditions -> discretization/solver -> convergence -> validation observable -> sensitivity/identifiability -> bounded mechanism claim`

### Reproducibility passport

Record:

- equation form, sign convention, coordinates, tensor and Voigt conventions;
- parameter value, units, temperature, source, transformation, and evidence status;
- geometry, dimensional reduction, interfaces, and symmetry assumptions;
- initial conditions, seeds, boundary conditions, and constraint implementation;
- mesh, domain/box size, time step, tolerance, solver, scaling, and stopping rule;
- total and component energy behavior where applicable;
- parameter sweep design and failed runs;
- code/model version and deterministic configuration reference.

### Required validation ladder

1. Analytical or limiting-case sanity check.
2. Mesh, time-step, box-size, and seed convergence as relevant.
3. Reproduction of a canonical trend or benchmark observable.
4. Sensitivity and parameter-identifiability assessment.
5. Comparison with an independent experiment or model when the claim crosses to reality.

### Alternative explanations and confounds

Check boundary-condition artifacts, periodic-box forcing, initialization bias, local minima, parameter mixing across incompatible sources, unit/tensor conversion errors, numerical diffusion, solver tolerances, omitted fields, and overfitting to a target image.

### Special time and topology cautions

- Do not map solver time or dimensionless TDGL time to physical time without a calibrated kinetic coefficient and validated dynamics.
- Do not treat an arrow plot as proof of winding, vorticity, chirality, topological charge, or thermodynamic stability.
- Do not interpret one converged solver state as the unique physical ground state without seed and energy comparisons.

### Claim boundary

A validated simulation can support mechanism plausibility and bounded predictions. It cannot by itself establish fabrication feasibility, experimental existence, device reliability, or system performance.

## Semiconductor devices

Lens key: `semiconductor-device`

### Required causal chain

`information/physical state -> band alignment and electrostatics -> transport mechanism -> geometry/process/interface -> terminal observable -> compact state law -> variability/reliability -> cell or circuit interface`

### Required device description

- material stack, geometry, electrodes, contacts, channel/barrier, interfaces, and process assumptions;
- controlled internal state and write/read/erase conditions;
- transport model and applicable bias/temperature regime;
- raw observable and extracted metric;
- state retention, endurance, cycle-to-cycle/device-to-device variation, and read disturb;
- area, energy, latency, compliance, calibration, and peripheral assumptions.

### Alternative mechanisms and confounds

Test contact resistance, Schottky barriers, trap charging, mobile ions/vacancies, filamentary paths, leakage, self-heating, capacitive transients, parasitic series resistance, geometry variation, and instrument limits. For FTJ or FeFET proxies, distinguish a calculated barrier/surface-potential/threshold shift from a measured device response.

### Baseline ladder

1. Null device or state without the proposed mechanism.
2. Conventional device using the same readout.
3. Strong mature device technology under matched voltage, area, time, accuracy, and retention.
4. Circuit-compatible model when circuit or compute value is claimed.

### Decisive evidence

Require a control that isolates the internal state, a readout that remains distinguishable under noise and variation, and an experiment or calibrated model that predicts failure boundaries. Report distributions rather than a hero device for reliability claims.

### Claim boundary

A WKB, surface-potential, threshold, or conductance proxy supports only the stated interface under its assumptions. It does not establish a fabricated device, compact model, array operability, or system advantage.

## Integrated circuits

Lens key: `integrated-circuit`

### Required causal chain

`measured/calibrated device behavior -> compact model -> cell -> array/interconnect -> peripheral circuits -> PVT and variation -> architecture/dataflow -> workload -> same-budget system metric`

### Required hierarchy

- compact-model calibration range and failure behavior;
- cell topology, write/read scheme, selectors, sensing, and disturb paths;
- array size, wire resistance/capacitance, sneak paths, IR drop, thermal coupling, and mapping;
- DAC/ADC, drivers, sense amplifiers, refresh, calibration, redundancy, and control overhead;
- process, voltage, temperature, aging, yield, mismatch, and Monte Carlo assumptions;
- architecture scheduling, data movement, utilization, precision, and algorithm mapping;
- workload, dataset, accuracy, latency, throughput, energy, area, and baseline budget.

### Baseline and fairness contract

Compare against the strongest practical CMOS/digital/analog alternative with matched precision, accuracy, batch size, technology assumptions, utilization, memory traffic, peripherals, and training/tuning budget. State whether metrics are measured, post-layout, circuit-simulated, architecture-simulated, or estimated.

### Alternative explanations and hidden costs

Check peripheral dominance, calibration amortization, refresh, error correction, low utilization, data conversion, interconnect, yield binning, temperature sensitivity, endurance management, and optimistic scaling assumptions.

### Decisive evidence

Use an executable compact-to-workload path with sensitivity to realistic device distributions and peripherals. A system claim should survive at least one adverse PVT/variation scenario and a same-budget baseline.

### Claim boundary

Do not promote a device curve or isolated cell simulation to IC value. Missing compact, array, peripheral, or workload bridges cap the claim at the last validated layer.

## Neuromorphic systems

Lens key: `neuromorphic-system`

### Required causal chain

`task and online constraint -> abstract computational principle -> state/update operation -> algorithm -> hardware primitive -> device-aware or hardware-in-loop realization -> non-biomimetic baseline -> ablation -> intrinsic gain and boundary`

### Problem definition

Specify whether the target is inference, continual/online learning, adaptation, prediction, reservoir dynamics, event processing, uncertainty, sensing-learning-action closure, or another operation. Define data arrival, label access, memory, compute, latency, energy, update locality, and nonstationarity budgets.

### Anti-biomimicry prior

Do not reason “the brain has function F, therefore copying biology in hardware is superior.” Require:

1. a biological observation, if used;
2. an abstract functional or computational principle that remains meaningful without biological language;
3. a mathematical operator or state/update rule;
4. an implementable hardware primitive;
5. a strong non-biomimetic baseline;
6. ablation of the claimed principle;
7. a measurable gain not explained only by more parameters, tuning, training, or hardware complexity.

### Evidence hierarchy

Label results as pure algorithm, ideal-device simulation, device-aware simulation, hardware-in-loop, single-device experiment, multi-device prototype, array, chip, or deployed closed loop. Never merge these levels in one performance claim.

### Alternative mechanisms and confounds

Check leakage of future labels, favorable task selection, extra state dimension, extra parameter count, hidden software training, device model fitting on test data, seed sensitivity, drift ignored in evaluation, energy excluding converters, and accuracy-energy tradeoffs.

### Baseline ladder

Use a same-budget digital or conventional algorithm, a device-neutral implementation of the same principle, and an ablation that removes the proposed physical dynamics. For continual learning, include memory/replay budget and task-order sensitivity; for reservoirs, include equal-state-dimension linear or digital reservoirs.

### Decisive evidence

The mechanism earns system relevance only if the principle-specific ablation degrades performance, the gain survives realistic variability and overhead, and a same-budget non-biomimetic baseline does not reproduce it cheaply.

### Claim boundary

Synapse-like curves, hysteresis, potentiation/depression, or temporal response alone do not establish learning, autonomy, energy efficiency, or biological fidelity.

## Wave and metasurface systems

Lens key: `wave-metasurface`

### Required causal chain

`target wave operation -> symmetry/resonance/dispersion/loss mechanism -> material/unit-cell parameters -> local response -> coupling and finite array -> tunability/control -> angle-bandwidth-efficiency behavior -> fabrication/measurement robustness -> application metric`

Apply the chain to electromagnetic, photonic, terahertz, acoustic, or elastic-wave surfaces while preserving domain-specific constitutive variables.

### Required system description

- frequency/wavelength, polarization, incidence angle, near/far field, and environment;
- constitutive material properties, dispersion, anisotropy, nonlinearity, and loss;
- unit-cell geometry, lattice, symmetry, boundary conditions, substrate, and conductor/dielectric models;
- phase/amplitude coverage, resonance Q, bandwidth, efficiency, aperture, side lobes, and scan range;
- control mechanism, bias network, tuning speed, power, resolution, and state stability;
- finite-size, mutual coupling, fabrication tolerance, packaging, calibration, and measurement setup.

### Alternative mechanisms and confounds

Check material loss, conductor loss, substrate modes, grating lobes, parasitic bias networks, local-periodic approximation failure, finite-aperture effects, angular sensitivity, polarization conversion, thermal drift, fabrication variation, and de-embedding/calibration error.

### Baseline ladder

Compare with a conventional phased array, diffractive optic, fixed metasurface, tunable bulk component, or mature active surface under matched aperture, bandwidth, efficiency, scan range, control power, fabrication tolerance, and system metric.

### Required validation ladder

1. Analytical or reduced-order mechanism sanity check.
2. Unit-cell full-wave simulation with material dispersion and loss.
3. Coupled/finite-array simulation and tolerance study.
4. Fabricated sample characterization with calibrated measurement.
5. Application-level demonstration under matched aperture and budget when application value is claimed.

### Claim boundary

An ideal periodic unit-cell simulation cannot establish finite-aperture efficiency, manufacturability, active-control overhead, measured bandwidth, or application-level superiority. Keep simulation and experiment labels explicit.

## Cross-domain handoffs

Every handoff needs an explicit bridge artifact or the higher-layer claim remains an inference.

| From | To | Minimum bridge |
|---|---|---|
| Materials/ferroelectric | Multiphysics model | Parameter provenance, state definition, boundary conditions, and a validation observable. |
| Multiphysics model | Semiconductor device | Geometry/stack mapping, electrostatic/transport coupling, calibrated output, and regime limits. |
| Materials/device | IC | Measured or calibrated compact model with variability, retention, endurance, and read/write behavior. |
| Device/IC | Neuromorphic system | State/update operator, hardware-in-loop level, same-budget baseline, overhead, and ablation. |
| Tunable material/device | Wave/metasurface | Frequency-dependent constitutive response, bias/control geometry, loss, and finite-array integration. |
| Wave/metasurface | IC/system | Control/readout electronics, calibration, interconnect, power, latency, and application budget. |

## Evidence ceilings across layers

- Simulation-only evidence supports model behavior, mechanism plausibility, and bounded predictions, not experimental existence.
- Single-device evidence supports a device effect, not population reliability, array operation, or chip metrics.
- Local-probe or concept-array evidence does not establish addressable arrays or integrated circuitry.
- Device-aware simulation does not equal hardware-in-loop or fabricated hardware.
- Unit-cell wave simulation does not establish finite-array or measured system performance.
- A biological analogy does not establish computational advantage.
- Any unvalidated cross-layer bridge caps the end-to-end claim at the last directly evidenced layer.

When a route spans several lenses, state the last validated layer, the next missing bridge, and the cheapest decisive test for that bridge.
