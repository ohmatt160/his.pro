import LegalDocument from "@/components/legal/LegalDocument";

const effectiveDate = "June 24, 2026";

const DataProcessingAgreement = () => (
  <LegalDocument
    title="Data Processing Agreement"
    effectiveDate={effectiveDate}
    summary="This DPA governs HIS.Pro's processing of personal data on behalf of a hospital or other healthcare customer and forms part of the customer's service agreement."
    sections={[
      {
        title: "Parties and scope",
        content: (
          <p>
            This DPA is between the healthcare organisation identified in the applicable order form
            (&quot;Customer&quot;) and the HIS.Pro operator identified there (&quot;HIS.Pro&quot;). It applies
            when HIS.Pro processes personal data for Customer in providing the service. Customer is the data
            controller and HIS.Pro is the data processor unless applicable law assigns a different role for a
            specific activity.
          </p>
        ),
      },
      {
        title: "Definitions and applicable law",
        content: (
          <p>
            &quot;Applicable Data Protection Law&quot; includes the Nigeria Data Protection Act 2023, binding
            regulations and directives issued under it, and other data protection laws applicable to the
            processing. Terms such as controller, processor, data subject, personal data, sensitive personal
            data, processing and personal data breach have the meanings given by applicable law.
          </p>
        ),
      },
      {
        title: "Customer instructions",
        content: (
          <p>
            HIS.Pro will process Customer Personal Data only on documented instructions contained in the
            service agreement, Customer&apos;s configured use of the service and lawful written instructions,
            unless law requires otherwise. HIS.Pro will notify Customer if an instruction appears to violate
            applicable data protection law, unless prohibited from doing so.
          </p>
        ),
      },
      {
        title: "Customer obligations",
        content: (
          <ul>
            <li>Ensure a lawful basis and any required condition for processing health and other sensitive data.</li>
            <li>Provide required privacy notices and manage consents where consent is relied upon.</li>
            <li>Limit data and user access to what is necessary and keep instructions accurate.</li>
            <li>Respond to data-subject requests and regulatory enquiries as controller.</li>
            <li>Configure retention, branches, roles, modules and exports consistently with applicable law.</li>
          </ul>
        ),
      },
      {
        title: "Confidentiality and personnel",
        content: (
          <p>
            HIS.Pro will ensure that personnel authorised to process Customer Personal Data are subject to
            confidentiality obligations, receive appropriate privacy and security guidance, and access data
            only to the extent required for their duties.
          </p>
        ),
      },
      {
        title: "Security measures",
        content: (
          <>
            <p>Taking account of risk, sensitivity, cost and the state of the art, HIS.Pro will maintain measures including:</p>
            <ul>
              <li>Tenant, facility, branch and role-based access restrictions.</li>
              <li>Encryption in transit and appropriate protection of stored data and backups.</li>
              <li>Password hashing, protected session cookies, rate limiting and session controls.</li>
              <li>Audit logging, security monitoring, vulnerability and dependency management.</li>
              <li>Secure development, change control, backup, recovery and incident-response procedures.</li>
              <li>Restricted privileged access and logical separation of production and staging environments.</li>
            </ul>
          </>
        ),
      },
      {
        title: "Personal data breaches",
        content: (
          <p>
            HIS.Pro will notify Customer without undue delay after confirming a personal data breach affecting
            Customer Personal Data. The notice will include available information reasonably required for
            Customer&apos;s assessment and regulatory duties. HIS.Pro will investigate, mitigate and provide
            reasonable cooperation. Customer remains responsible for notifications it must make as controller.
          </p>
        ),
      },
      {
        title: "Data-subject requests",
        content: (
          <p>
            If HIS.Pro receives a request concerning Customer Personal Data, it will direct the requester to
            Customer unless authorised or legally required to respond. Taking account of the nature of
            processing, HIS.Pro will provide reasonable technical and organisational assistance for access,
            correction, deletion, restriction, objection, portability and related rights.
          </p>
        ),
      },
      {
        title: "Regulatory and compliance assistance",
        content: (
          <p>
            HIS.Pro will provide reasonable information and assistance for Customer&apos;s security assessments,
            breach duties, data protection impact assessments and consultations with a competent authority,
            considering the nature of processing and information available to HIS.Pro.
          </p>
        ),
      },
      {
        title: "Subprocessors",
        content: (
          <>
            <p>
              Customer gives general authorisation for HIS.Pro to use subprocessors needed to provide hosting,
              database, storage, communications, support and security services. HIS.Pro will impose data
              protection obligations materially equivalent to this DPA and remains responsible for its
              subprocessor obligations to the extent required by law.
            </p>
            <p>
              HIS.Pro will make current subprocessor information available and provide reasonable notice of a
              new subprocessor that will process Customer Personal Data. Customer may object on reasonable,
              documented data-protection grounds.
            </p>
          </>
        ),
      },
      {
        title: "International transfers",
        content: (
          <p>
            HIS.Pro will not transfer Customer Personal Data internationally unless permitted by applicable
            law and protected by an approved transfer mechanism, adequacy basis, contractual safeguards or
            another valid legal basis. Customer authorises transfers necessary for approved subprocessors
            identified under this DPA.
          </p>
        ),
      },
      {
        title: "Audits",
        content: (
          <p>
            On reasonable written request, HIS.Pro will provide information necessary to demonstrate compliance.
            If that information is insufficient, Customer may conduct or commission a proportionate audit no
            more than once annually, unless a breach or regulator requires otherwise. Audits must protect other
            customers, security, confidentiality and service availability, and avoid access to another tenant&apos;s data.
          </p>
        ),
      },
      {
        title: "Return and deletion",
        content: (
          <p>
            At termination or Customer&apos;s documented request, HIS.Pro will make Customer Personal Data
            available for export where included in the service and then delete or return it, unless retention is
            legally required. Data may remain in protected backups until ordinary expiry, during which this DPA
            continues to apply and the data will not be restored except for recovery or legal necessity.
          </p>
        ),
      },
      {
        title: "Processing details",
        content: (
          <>
            <p><strong>Subject matter:</strong> Provision, hosting, security, maintenance and support of HIS.Pro.</p>
            <p><strong>Duration:</strong> The service term plus agreed export, backup and deletion periods.</p>
            <p>
              <strong>Nature and purpose:</strong> Storage, retrieval, organisation, transmission, access,
              reporting, workflow management, backup, support and security at Customer&apos;s instruction.
            </p>
            <p>
              <strong>Data subjects:</strong> Patients, relatives and emergency contacts, hospital staff,
              clinicians, contractors, suppliers and other persons recorded by Customer.
            </p>
            <p>
              <strong>Data categories:</strong> Identity and contact data; demographics; health and clinical
              records; appointments; prescriptions; laboratory and radiology information; ward data; billing,
              payment and insurance information; communications; audit, device and security data.
            </p>
            <p>
              <strong>Sensitive data:</strong> Health, biometric or genetic information where entered, and any
              other sensitive personal data processed by Customer through the service.
            </p>
          </>
        ),
      },
      {
        title: "Order of precedence and execution",
        content: (
          <p>
            If this DPA conflicts with the service agreement on personal-data processing, this DPA controls.
            Customer accepts this DPA by signing an order form that incorporates it, signing a copy, or using
            the service after being presented with it. Enterprise customers may request an execution copy from{" "}
            <a href="mailto:legal@his.pro">legal@his.pro</a>.
          </p>
        ),
      },
    ]}
  />
);

export default DataProcessingAgreement;
