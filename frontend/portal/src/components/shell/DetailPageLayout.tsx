import { Children, Fragment, type PropsWithChildren, type ReactNode } from "react";

interface DetailPageLayoutProps extends PropsWithChildren {
  className?: string;
  sectionWrapper?: (input: { index: number; section: ReactNode }) => ReactNode;
}

export function DetailPageLayout({
  children,
  className,
  sectionWrapper,
}: DetailPageLayoutProps) {
  const sections = Children.toArray(children);
  const layoutClassName = className
    ? `portal-stacked-sections ${className}`
    : "portal-stacked-sections";

  return (
    <div className={layoutClassName}>
      {sections.map((section, index) => (
        <Fragment
          key={
            typeof section === "object" &&
            section !== null &&
            "key" in section &&
            section.key != null
              ? String(section.key)
              : `section-${index}`
          }
        >
          {sectionWrapper ? sectionWrapper({ index, section }) : section}
          {index < sections.length - 1 ? <SectionDivider /> : null}
        </Fragment>
      ))}
    </div>
  );
}

interface SectionBlockProps extends PropsWithChildren {
  as?: "div" | "section";
  className?: string;
}

export function SectionBlock({
  as: Component = "section",
  children,
  className,
}: SectionBlockProps) {
  return <Component className={className}>{children}</Component>;
}

export function SectionDivider() {
  return (
    <hr
      aria-hidden="true"
      className="portal-stacked-sections__divider"
      role="presentation"
    />
  );
}
