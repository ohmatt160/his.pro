import LegalDocument from "@/components/legal/LegalDocument";

const effectiveDate = "June 24, 2026";

const PrivacyPolicy = () => (
  <LegalDocument
    title="Privacy Policy"
    effectiveDate={effectiveDate}
    summary="This policy explains how HIS.Pro handles personal data when people visit our website, create or administer a hospital workspace, use the service as authorised staff, or contact us."
    sections={[
      {
        title: "Who this policy applies to",
        content: (
          <>
            <p>
              This policy applies to HIS.Pro website visitors, hospital administrators, authorised
              workforce users, prospective customers, and people who contact us. The HIS.Pro operator
              identified in the applicable order form or service agreement is responsible for the
              activities described in this policy.
            </p>
            <p>
              For patient records and hospital workforce records placed in a workspace, the hospital
              generally determines why and how the data is used and acts as the <strong>data controller</strong>.
              HIS.Pro acts as its <strong>data processor</strong>. Patients and staff should normally direct
              requests about hospital records to the relevant hospital.
            </p>
          </>
        ),
      },
      {
        title: "Data we collect",
        content: (
          <>
            <p>Depending on how the service is used, we may process:</p>
            <ul>
              <li>Account and identity data, including names, login identifiers, roles and contact details.</li>
              <li>Facility, branch, department, subscription and billing information.</li>
              <li>Security and audit data, including IP address, browser, device, timestamps and user activity.</li>
              <li>Support communications, feedback and service correspondence.</li>
              <li>
                Hospital-controlled data, including patient demographics, appointments, clinical records,
                prescriptions, laboratory and radiology orders, billing records and uploaded files.
              </li>
            </ul>
            <p>We do not sell personal data or use hospital-controlled health data for advertising.</p>
          </>
        ),
      },
      {
        title: "Why we process data",
        content: (
          <ul>
            <li>Provide, secure, maintain and support the service.</li>
            <li>Authenticate users, enforce roles and isolate hospital and branch data.</li>
            <li>Process subscriptions, invoices and customer communications.</li>
            <li>Detect abuse, investigate incidents, maintain audit trails and meet legal obligations.</li>
            <li>Improve reliability and performance using appropriately limited operational information.</li>
            <li>Process hospital-controlled data only on documented customer instructions.</li>
          </ul>
        ),
      },
      {
        title: "Legal bases",
        content: (
          <p>
            Where applicable, processing is based on performance of a contract, compliance with legal
            obligations, legitimate interests in operating and securing the service, consent where required,
            and the lawful bases selected by each hospital for its own clinical and employment processing.
            Health information is sensitive personal data and must receive enhanced protection.
          </p>
        ),
      },
      {
        title: "Sharing and service providers",
        content: (
          <>
            <p>
              We share data only where necessary with authorised hospital users, infrastructure and hosting
              providers, database and storage providers, communications providers, professional advisers,
              payment providers, and public authorities where legally required.
            </p>
            <p>
              Providers handling hospital-controlled data are engaged under appropriate confidentiality,
              security and data-processing obligations. Current subprocessors may be identified in the
              applicable service agreement or subprocessor notice.
            </p>
          </>
        ),
      },
      {
        title: "International transfers",
        content: (
          <p>
            Data may be processed outside the user&apos;s country where our approved infrastructure or support
            providers operate. We use contractual and organisational safeguards required by applicable data
            protection law and consider the sensitivity of health information before enabling a processing
            location.
          </p>
        ),
      },
      {
        title: "Security",
        content: (
          <p>
            We use role-based access controls, tenant and branch isolation, encryption in transit, protected
            authentication cookies, password hashing, audit logging, input validation, rate limiting, backups,
            monitoring and restricted administrative access. No system is risk-free, and customers must manage
            authorised users, devices, passwords, exports and local operating procedures securely.
          </p>
        ),
      },
      {
        title: "Retention and deletion",
        content: (
          <p>
            Account, contract, security and billing records are retained only as long as reasonably required
            for service delivery, legal compliance, dispute resolution and security. Hospital-controlled data
            is retained according to the hospital&apos;s instructions, configured retention requirements and
            applicable healthcare law. Backup copies may remain for a limited recovery period before deletion
            or irreversible overwrite.
          </p>
        ),
      },
      {
        title: "Your rights",
        content: (
          <>
            <p>
              Subject to applicable law, individuals may have rights to information, access, correction,
              deletion, restriction, objection, portability, withdrawal of consent and review of qualifying
              automated decisions. Identity verification may be required.
            </p>
            <p>
              Requests about hospital records should be sent to the hospital. Other privacy requests may be
              sent to <a href="mailto:privacy@his.pro">privacy@his.pro</a>. Individuals may also complain to
              the Nigeria Data Protection Commission or another competent supervisory authority.
            </p>
          </>
        ),
      },
      {
        title: "Cookies and local device storage",
        content: (
          <p>
            We use strictly necessary cookies and browser storage for authentication, session continuity,
            security and workspace preferences. We do not place authentication tokens in local storage.
            Optional analytics or marketing technologies will require any consent mandated by law.
          </p>
        ),
      },
      {
        title: "Children, changes and contact",
        content: (
          <>
            <p>
              HIS.Pro is provided to healthcare organisations and authorised workforce users, not directly to
              children. Hospitals remain responsible for lawful processing of paediatric records.
            </p>
            <p>
              We may update this policy to reflect legal, operational or service changes. Material changes will
              be communicated through the service or customer contact channels. Questions can be sent to{" "}
              <a href="mailto:privacy@his.pro">privacy@his.pro</a>.
            </p>
          </>
        ),
      },
    ]}
  />
);

export default PrivacyPolicy;
