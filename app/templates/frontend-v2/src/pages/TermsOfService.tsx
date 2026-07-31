import LegalDocument from "@/components/legal/LegalDocument";

const effectiveDate = "June 24, 2026";

const TermsOfService = () => (
  <LegalDocument
    title="Terms of Service"
    effectiveDate={effectiveDate}
    summary="These terms govern access to and use of HIS.Pro by healthcare organisations and their authorised users. A signed order form or enterprise agreement may add or replace specific terms."
    sections={[
      {
        title: "Agreement and authority",
        content: (
          <p>
            By creating a workspace, signing an order form or using HIS.Pro, the customer agrees to these terms
            and confirms that the person acting for it has authority to bind the healthcare organisation.
            If an order form conflicts with these terms, the order form controls for that conflict.
          </p>
        ),
      },
      {
        title: "The service",
        content: (
          <p>
            HIS.Pro provides modular hospital information-system functionality selected by the customer.
            Features, storage, support and usage limits depend on the applicable plan. We may improve the
            service provided that we do not materially reduce paid core functionality during a current term.
          </p>
        ),
      },
      {
        title: "Customer responsibilities",
        content: (
          <ul>
            <li>Use the service only for lawful healthcare and administrative purposes.</li>
            <li>Maintain accurate facility, user, role, branch and module configuration.</li>
            <li>Authorise only appropriate workforce users and promptly disable unnecessary access.</li>
            <li>Maintain lawful notices, consents, clinical policies, retention schedules and patient rights processes.</li>
            <li>Verify clinical decisions independently; HIS.Pro does not practise medicine or replace professional judgment.</li>
            <li>Protect devices, credentials, exports and networks under the customer&apos;s control.</li>
          </ul>
        ),
      },
      {
        title: "Acceptable use",
        content: (
          <p>
            Users must not access another tenant or branch without authorisation, bypass security controls,
            probe vulnerabilities without written permission, upload malicious content, interfere with service
            availability, misuse personal data, reverse engineer protected components except where law permits,
            or use the service to violate patient rights or applicable law.
          </p>
        ),
      },
      {
        title: "Accounts and security",
        content: (
          <p>
            Accounts are individual and must not be shared. The customer is responsible for actions taken by
            its authorised users and must notify HIS.Pro promptly of suspected compromise. We may suspend a
            session or account where reasonably necessary to protect patients, customers, the service or third parties.
          </p>
        ),
      },
      {
        title: "Fees, taxes and renewal",
        content: (
          <p>
            Fees, billing periods, usage limits and renewal terms are stated in the order form or plan selected
            by the customer. Fees exclude applicable taxes unless expressly stated. Overdue undisputed amounts
            may result in restricted access after reasonable notice, subject to applicable law and agreed data-access arrangements.
          </p>
        ),
      },
      {
        title: "Customer data and privacy",
        content: (
          <>
            <p>
              The customer retains its rights in customer data. It grants HIS.Pro the limited right to host,
              copy, transmit and otherwise process that data solely to provide, secure and support the service.
            </p>
            <p>
              The <a href="/privacy">Privacy Policy</a> describes our own privacy practices. The{" "}
              <a href="/dpa">Data Processing Agreement</a> applies where HIS.Pro processes personal data for a customer.
            </p>
          </>
        ),
      },
      {
        title: "Confidentiality",
        content: (
          <p>
            Each party must protect the other&apos;s non-public business, technical, security and personal
            information using at least reasonable care, use it only for the agreement, and disclose it only to
            people who need it and are bound by confidentiality, unless disclosure is legally required.
          </p>
        ),
      },
      {
        title: "Availability, support and changes",
        content: (
          <p>
            We aim to provide a reliable service but do not promise uninterrupted availability unless a signed
            service-level agreement says otherwise. Maintenance, internet failures, third-party infrastructure,
            emergencies and events beyond reasonable control may affect availability. Customers should maintain
            clinically appropriate downtime and continuity procedures.
          </p>
        ),
      },
      {
        title: "Intellectual property",
        content: (
          <p>
            HIS.Pro and its licensors retain all rights in the service, software, documentation and branding.
            The customer receives a limited, non-exclusive, non-transferable right to use the service during the
            subscription term. Feedback may be used without identifying the customer or disclosing confidential information.
          </p>
        ),
      },
      {
        title: "Suspension and termination",
        content: (
          <p>
            Either party may terminate as stated in the order form or for an uncured material breach. We may
            suspend access immediately where necessary to address a serious security, legal or patient-safety
            risk. Following termination, export and deletion of customer data will follow the order form and DPA.
          </p>
        ),
      },
      {
        title: "Warranties and disclaimers",
        content: (
          <p>
            Each party warrants that it has authority to enter the agreement. Except for express commitments,
            the service is provided on an &quot;as available&quot; basis to the extent permitted by law. HIS.Pro
            does not warrant that the service will diagnose, treat or prevent any condition, or that customer-entered
            data is complete or clinically correct.
          </p>
        ),
      },
      {
        title: "Liability",
        content: (
          <p>
            Liability limitations, exclusions and any agreed cap should be stated in the applicable order form.
            Nothing excludes liability that cannot lawfully be excluded, including liability arising from fraud
            or other matters for which exclusion is prohibited. Enterprise customers should obtain negotiated
            terms appropriate to clinical risk and subscription value.
          </p>
        ),
      },
      {
        title: "Governing law and contact",
        content: (
          <p>
            Unless an order form states otherwise, these terms are governed by the laws of the Federal Republic
            of Nigeria, and disputes are subject to the courts agreed in the order form. Legal notices may be sent
            to <a href="mailto:legal@his.pro">legal@his.pro</a> and to the customer contact listed in its account.
          </p>
        ),
      },
    ]}
  />
);

export default TermsOfService;
