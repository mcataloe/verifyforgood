import { Children, Fragment, type PropsWithChildren, type ReactNode } from "react";

interface StackedDetailSectionsProps extends PropsWithChildren {
  className?: string;
  sectionWrapper?: (input: { index: number; section: ReactNode }) => ReactNode;
}

export function StackedDetailSections({
  children,
  className,
  sectionWrapper,
}: StackedDetailSectionsProps) {
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
          {index < sections.length - 1 ? (
            <hr
              aria-hidden="true"
              className="portal-stacked-sections__divider"
              role="presentation"
            />
          ) : null}
        </Fragment>
      ))}
    </div>
  );
}
